// Ghidra headless post-script.
// Arguments: <comma_separated_function_names> <output_dir> <metadata_path>

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;

import java.io.File;
import java.io.FileWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class ExportNamedFunctionsDecomp extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 3) {
            throw new IllegalArgumentException(
                "usage: ExportNamedFunctionsDecomp.java <comma_separated_function_names> <output_dir> <metadata_path>"
            );
        }

        Set<String> wanted = new HashSet<>();
        for (String rawName : args[0].split(",")) {
            String name = rawName.trim();
            if (!name.isEmpty()) {
                wanted.add(name);
            }
        }
        File outputDir = new File(args[1]);
        File metadata = new File(args[2]);
        outputDir.mkdirs();
        metadata.getParentFile().mkdirs();

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        List<String> metadataItems = new ArrayList<>();
        int decompiledCount = 0;
        int missingCount = 0;

        for (String functionName : wanted) {
            Function target = findFunction(functionName);
            if (target == null) {
                missingCount++;
                metadataItems.add(
                    "{\"function_name\":\"" + escape(functionName) + "\",\"status\":\"missing_function\"}"
                );
                continue;
            }

            DecompileResults results = decompiler.decompileFunction(target, 120, monitor);
            String status = results.decompileCompleted() ? "decompiled" : "decompile_failed";
            String cCode = "";
            if (results.getDecompiledFunction() != null) {
                cCode = results.getDecompiledFunction().getC();
            }
            File outputC = new File(outputDir, functionName + ".c");
            try (FileWriter writer = new FileWriter(outputC, StandardCharsets.UTF_8)) {
                writer.write(cCode);
                if (!cCode.endsWith("\n")) {
                    writer.write("\n");
                }
            }
            if (results.decompileCompleted() && !cCode.isBlank()) {
                decompiledCount++;
            }
            String errorMessage = results.getErrorMessage();
            metadataItems.add(
                "{"
                    + "\"function_name\":\"" + escape(functionName) + "\","
                    + "\"status\":\"" + escape(status) + "\","
                    + "\"entry\":\"" + escape(target.getEntryPoint().toString()) + "\","
                    + "\"signature\":\"" + escape(target.getSignature().toString()) + "\","
                    + "\"error\":\"" + escape(errorMessage == null ? "" : errorMessage) + "\","
                    + "\"c_size\":" + cCode.length() + ","
                    + "\"output_path\":\"" + escape(outputC.getAbsolutePath()) + "\""
                    + "}"
            );
        }

        Files.writeString(
            metadata.toPath(),
            "{"
                + "\"requested_count\":" + wanted.size() + ","
                + "\"decompiled_count\":" + decompiledCount + ","
                + "\"missing_count\":" + missingCount + ","
                + "\"functions\":[" + String.join(",", metadataItems) + "]"
                + "}\n",
            StandardCharsets.UTF_8
        );
        decompiler.dispose();
    }

    private Function findFunction(String functionName) {
        for (Function function : currentProgram.getFunctionManager().getFunctions(true)) {
            if (function.getName().equals(functionName)) {
                return function;
            }
        }
        return null;
    }

    private static String escape(String value) {
        return value
            .replace("\\", "\\\\")
            .replace("\"", "\\\"")
            .replace("\n", "\\n")
            .replace("\r", "\\r");
    }
}
