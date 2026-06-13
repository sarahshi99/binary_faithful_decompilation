from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from analysis.decompile_faithfulness.compile import run_command


@dataclass(frozen=True)
class BinaryFeatureVector:
    object_path: Path
    instruction_count: int
    branch_count: int
    call_count: int
    ret_count: int
    opcode_counts: dict[str, int]
    instruction_signature_counts: dict[str, int]
    immediates: set[str]
    symbols: set[str]


@dataclass(frozen=True)
class FeatureDistance:
    total: float
    components: dict[str, float]


_INSTRUCTION_RE = re.compile(r"^\s*[0-9a-fA-F]+:\s+(?:[0-9a-fA-F]{2}\s+)+\s*(?P<text>.*)$")
_IMMEDIATE_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:0x[0-9a-fA-F]+|\d+)")


def extract_binary_features(object_path: Path) -> BinaryFeatureVector:
    objdump = run_command(["/usr/bin/objdump", "-d", str(object_path)])
    nm = run_command(["/usr/bin/nm", "--defined-only", str(object_path)])
    if objdump.returncode != 0:
        raise RuntimeError(objdump.stderr)
    if nm.returncode != 0:
        raise RuntimeError(nm.stderr)

    opcode_counts: Counter[str] = Counter()
    instruction_signature_counts: Counter[str] = Counter()
    immediates: set[str] = set()
    branch_count = 0
    call_count = 0
    ret_count = 0

    for line in objdump.stdout.splitlines():
        match = _INSTRUCTION_RE.match(line)
        if not match:
            continue
        text = match.group("text").strip()
        if not text:
            continue
        parts = text.split(None, 1)
        opcode = parts[0].lower()
        operands = parts[1] if len(parts) > 1 else ""
        opcode_counts[opcode] += 1
        instruction_signature_counts[_instruction_signature(opcode, operands)] += 1
        if opcode.startswith("j"):
            branch_count += 1
        if opcode.startswith("call"):
            call_count += 1
        if opcode.startswith("ret"):
            ret_count += 1
        immediates.update(_normalize_immediate(value) for value in _IMMEDIATE_RE.findall(operands))

    symbols = _parse_symbols(nm.stdout)
    return BinaryFeatureVector(
        object_path=object_path,
        instruction_count=sum(opcode_counts.values()),
        branch_count=branch_count,
        call_count=call_count,
        ret_count=ret_count,
        opcode_counts=dict(opcode_counts),
        instruction_signature_counts=dict(instruction_signature_counts),
        immediates=immediates,
        symbols=symbols,
    )


def feature_distance(left: BinaryFeatureVector, right: BinaryFeatureVector) -> FeatureDistance:
    opcodes = set(left.opcode_counts) | set(right.opcode_counts)
    signatures = set(left.instruction_signature_counts) | set(right.instruction_signature_counts)
    components = {
        "instruction_count_abs": float(abs(left.instruction_count - right.instruction_count)),
        "branch_count_abs": float(abs(left.branch_count - right.branch_count)),
        "call_count_abs": float(abs(left.call_count - right.call_count)),
        "ret_count_abs": float(abs(left.ret_count - right.ret_count)),
        "opcode_l1": float(
            sum(abs(left.opcode_counts.get(opcode, 0) - right.opcode_counts.get(opcode, 0)) for opcode in opcodes)
        ),
        "instruction_signature_l1": float(
            sum(
                abs(
                    left.instruction_signature_counts.get(signature, 0)
                    - right.instruction_signature_counts.get(signature, 0)
                )
                for signature in signatures
            )
        ),
        "immediate_symmetric_diff": float(len(left.immediates ^ right.immediates)),
        "symbol_symmetric_diff": float(len(left.symbols ^ right.symbols)),
    }
    return FeatureDistance(total=sum(components.values()), components=components)


def _parse_symbols(stdout: str) -> set[str]:
    symbols: set[str] = set()
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            symbols.add(parts[-1])
    return symbols


def _normalize_immediate(value: str) -> str:
    if value.lower().startswith(("0x", "+0x", "-0x")):
        sign = "-" if value.startswith("-") else ""
        hex_part = value[1:] if value[0] in "+-" else value
        return f"{sign}{int(hex_part, 16)}"
    return str(int(value, 10))


def _instruction_signature(opcode: str, operands: str) -> str:
    normalized = re.sub(r"\s*<[^>]+>", "", operands)
    normalized = _IMMEDIATE_RE.sub(lambda match: _normalize_immediate(match.group(0)), normalized)
    normalized = re.sub(r"\s+", "", normalized)
    return f"{opcode} {normalized}" if normalized else opcode
