// Ghidra headless post-script.
// Arguments: <function_name> <output_c_path> <metadata_path>

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;

import java.io.File;
import java.io.FileWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

public class ExportFunctionDecomp extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 3) {
            throw new IllegalArgumentException(
                "usage: ExportFunctionDecomp.java <function_name> <output_c_path> <metadata_path>"
            );
        }

        String functionName = args[0];
        File outputC = new File(args[1]);
        File metadata = new File(args[2]);
        outputC.getParentFile().mkdirs();
        metadata.getParentFile().mkdirs();

        Function target = null;
        for (Function function : currentProgram.getFunctionManager().getFunctions(true)) {
            if (function.getName().equals(functionName)) {
                target = function;
                break;
            }
        }

        if (target == null) {
            Files.writeString(
                metadata.toPath(),
                "{\"status\":\"missing_function\",\"function_name\":\"" + escape(functionName) + "\"}\n",
                StandardCharsets.UTF_8
            );
            return;
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        DecompileResults results = decompiler.decompileFunction(target, 120, monitor);
        String status = results.decompileCompleted() ? "decompiled" : "decompile_failed";
        String cCode = "";
        if (results.getDecompiledFunction() != null) {
            cCode = results.getDecompiledFunction().getC();
        }
        try (FileWriter writer = new FileWriter(outputC, StandardCharsets.UTF_8)) {
            writer.write(cCode);
            if (!cCode.endsWith("\n")) {
                writer.write("\n");
            }
        }
        String errorMessage = results.getErrorMessage();
        Files.writeString(
            metadata.toPath(),
            "{"
                + "\"status\":\"" + escape(status) + "\","
                + "\"function_name\":\"" + escape(functionName) + "\","
                + "\"entry\":\"" + escape(target.getEntryPoint().toString()) + "\","
                + "\"signature\":\"" + escape(target.getSignature().toString()) + "\","
                + "\"error\":\"" + escape(errorMessage == null ? "" : errorMessage) + "\","
                + "\"c_size\":" + cCode.length()
                + "}\n",
            StandardCharsets.UTF_8
        );
        decompiler.dispose();
    }

    private static String escape(String value) {
        return value
            .replace("\\", "\\\\")
            .replace("\"", "\\\"")
            .replace("\n", "\\n")
            .replace("\r", "\\r");
    }
}
