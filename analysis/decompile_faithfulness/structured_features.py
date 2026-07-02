from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from analysis.decompile_faithfulness.compile import run_command


@dataclass(frozen=True)
class StructuredInstruction:
    address: int
    opcode: str
    operands: str
    target: int | None = None


@dataclass(frozen=True)
class BasicBlock:
    start_address: int
    instructions: tuple[StructuredInstruction, ...]
    terminal_opcode: str
    successors: tuple[int, ...]


@dataclass(frozen=True)
class StructuredFeatureVector:
    object_path: Path
    instruction_count: int
    block_count: int
    basic_block_shape_counts: dict[str, int]
    terminal_opcode_counts: dict[str, int]
    cfg_edge_motif_counts: dict[str, int]
    branch_return_binding_counts: dict[str, int]
    compare_branch_return_counts: dict[str, int]
    loop_update_binding_counts: dict[str, int]


_INSTRUCTION_RE = re.compile(
    r"^\s*(?P<address>[0-9a-fA-F]+):\s+"
    r"(?:(?:[0-9a-fA-F]{2})\s+)+\s*"
    r"(?P<text>.*)$"
)
_TARGET_RE = re.compile(r"^(?:0x)?(?P<target>[0-9a-fA-F]+)(?:\s+<[^>]+>)?$")
_IMMEDIATE_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:0x[0-9a-fA-F]+|\d+)")
_RETURN_REGISTERS = ("%eax", "%rax")


def parse_objdump_instructions(text: str) -> list[StructuredInstruction]:
    instructions: list[StructuredInstruction] = []
    for line in text.splitlines():
        match = _INSTRUCTION_RE.match(line)
        if not match:
            continue
        instruction_text = match.group("text").strip()
        if not instruction_text:
            continue
        parts = instruction_text.split(None, 1)
        opcode = parts[0].lower()
        operands = parts[1].strip() if len(parts) > 1 else ""
        instructions.append(
            StructuredInstruction(
                address=int(match.group("address"), 16),
                opcode=opcode,
                operands=operands,
                target=_parse_target(opcode, operands),
            )
        )
    return instructions


def build_basic_blocks(instructions: list[StructuredInstruction]) -> list[BasicBlock]:
    if not instructions:
        return []

    address_to_index = {instruction.address: index for index, instruction in enumerate(instructions)}
    leaders = {instructions[0].address}
    for index, instruction in enumerate(instructions):
        if instruction.target is not None:
            leaders.add(instruction.target)
        if _ends_basic_block(instruction.opcode) and index + 1 < len(instructions):
            leaders.add(instructions[index + 1].address)

    leader_indices = sorted(
        address_to_index[address]
        for address in leaders
        if address in address_to_index
    )
    blocks_without_successors: list[tuple[int, tuple[StructuredInstruction, ...]]] = []
    for position, start_index in enumerate(leader_indices):
        end_index = leader_indices[position + 1] if position + 1 < len(leader_indices) else len(instructions)
        block_instructions = tuple(instructions[start_index:end_index])
        if block_instructions:
            blocks_without_successors.append((block_instructions[0].address, block_instructions))

    block_starts = [start for start, _block_instructions in blocks_without_successors]
    blocks: list[BasicBlock] = []
    for position, (start_address, block_instructions) in enumerate(blocks_without_successors):
        terminal = block_instructions[-1]
        fallthrough = block_starts[position + 1] if position + 1 < len(block_starts) else None
        successors = _successors_for_terminal(terminal, fallthrough)
        blocks.append(
            BasicBlock(
                start_address=start_address,
                instructions=block_instructions,
                terminal_opcode=terminal.opcode,
                successors=successors,
            )
        )
    return blocks


def features_from_instructions(
    instructions: list[StructuredInstruction],
    object_path: Path,
) -> StructuredFeatureVector:
    blocks = build_basic_blocks(instructions)
    by_address = {block.start_address: block for block in blocks}

    block_shapes: Counter[str] = Counter()
    terminal_opcodes: Counter[str] = Counter()
    cfg_edges: Counter[str] = Counter()
    branch_return_bindings: Counter[str] = Counter()
    compare_branch_returns: Counter[str] = Counter()
    loop_update_bindings: Counter[str] = Counter()

    for block in blocks:
        terminal_opcodes[block.terminal_opcode] += 1
        block_shapes[_block_shape(block)] += 1
        _add_cfg_edge_motifs(block, by_address, cfg_edges)
        _add_branch_return_motifs(
            block,
            by_address,
            branch_return_bindings,
            compare_branch_returns,
        )
        _add_loop_update_motifs(block, by_address, loop_update_bindings)

    return StructuredFeatureVector(
        object_path=object_path,
        instruction_count=len(instructions),
        block_count=len(blocks),
        basic_block_shape_counts=dict(block_shapes),
        terminal_opcode_counts=dict(terminal_opcodes),
        cfg_edge_motif_counts=dict(cfg_edges),
        branch_return_binding_counts=dict(branch_return_bindings),
        compare_branch_return_counts=dict(compare_branch_returns),
        loop_update_binding_counts=dict(loop_update_bindings),
    )


def extract_structured_features(object_path: Path) -> StructuredFeatureVector:
    objdump = run_command(["/usr/bin/objdump", "-d", str(object_path)])
    if objdump.returncode != 0:
        raise RuntimeError(objdump.stderr)
    return features_from_instructions(parse_objdump_instructions(objdump.stdout), object_path)


def structured_feature_distance(
    left: StructuredFeatureVector,
    right: StructuredFeatureVector,
) -> dict[str, float]:
    components = {
        "basic_block_shape_l1": _counter_l1(left.basic_block_shape_counts, right.basic_block_shape_counts),
        "terminal_opcode_l1": _counter_l1(left.terminal_opcode_counts, right.terminal_opcode_counts),
        "cfg_edge_motif_l1": _counter_l1(left.cfg_edge_motif_counts, right.cfg_edge_motif_counts),
        "branch_return_binding_l1": _counter_l1(
            left.branch_return_binding_counts,
            right.branch_return_binding_counts,
        ),
        "compare_branch_return_l1": _counter_l1(
            left.compare_branch_return_counts,
            right.compare_branch_return_counts,
        ),
        "loop_update_binding_l1": _counter_l1(
            left.loop_update_binding_counts,
            right.loop_update_binding_counts,
        ),
    }
    components["structured_binding_total"] = (
        components["cfg_edge_motif_l1"]
        + components["branch_return_binding_l1"]
        + components["compare_branch_return_l1"]
        + components["loop_update_binding_l1"]
    )
    return components


def _parse_target(opcode: str, operands: str) -> int | None:
    if not opcode.startswith(("j", "call")):
        return None
    first_operand = operands.split(",", 1)[0].strip()
    if first_operand.startswith("*"):
        return None
    match = _TARGET_RE.match(first_operand)
    if not match:
        return None
    return int(match.group("target"), 16)


def _ends_basic_block(opcode: str) -> bool:
    return opcode.startswith("j") or opcode.startswith("ret")


def _successors_for_terminal(
    terminal: StructuredInstruction,
    fallthrough: int | None,
) -> tuple[int, ...]:
    if _is_conditional_jump(terminal.opcode):
        successors = []
        if terminal.target is not None:
            successors.append(terminal.target)
        if fallthrough is not None:
            successors.append(fallthrough)
        return tuple(successors)
    if _is_unconditional_jump(terminal.opcode):
        return (terminal.target,) if terminal.target is not None else ()
    if terminal.opcode.startswith("ret"):
        return ()
    return (fallthrough,) if fallthrough is not None else ()


def _is_conditional_jump(opcode: str) -> bool:
    return opcode.startswith("j") and not _is_unconditional_jump(opcode)


def _is_unconditional_jump(opcode: str) -> bool:
    return opcode in {"jmp", "jmpq"}


def _block_shape(block: BasicBlock) -> str:
    return f"len:{len(block.instructions)}|term:{block.terminal_opcode}|succ:{len(block.successors)}"


def _add_cfg_edge_motifs(
    block: BasicBlock,
    by_address: dict[int, BasicBlock],
    cfg_edges: Counter[str],
) -> None:
    if not block.successors:
        return
    if _is_conditional_jump(block.terminal_opcode):
        target_kind = _block_terminal_kind(by_address.get(block.successors[0]))
        fallthrough_kind = _block_terminal_kind(by_address.get(block.successors[1])) if len(block.successors) > 1 else "none"
        cfg_edges[f"{block.terminal_opcode}->target:{target_kind}|fallthrough:{fallthrough_kind}"] += 1
        return
    for successor in block.successors:
        cfg_edges[f"{block.terminal_opcode}->{_block_terminal_kind(by_address.get(successor))}"] += 1


def _add_branch_return_motifs(
    block: BasicBlock,
    by_address: dict[int, BasicBlock],
    branch_return_bindings: Counter[str],
    compare_branch_returns: Counter[str],
) -> None:
    terminal = block.instructions[-1] if block.instructions else None
    if terminal is None or not _is_conditional_jump(terminal.opcode) or len(block.successors) < 2:
        return

    target_return = _return_value_from_path(block.successors[0], by_address)
    fallthrough_return = _return_value_from_path(block.successors[1], by_address)
    if target_return is None or fallthrough_return is None:
        return

    binding = (
        f"{terminal.opcode}->target_return:{target_return}"
        f"|fallthrough_return:{fallthrough_return}"
    )
    branch_return_bindings[binding] += 1

    compare_immediate = _nearest_compare_immediate(block.instructions[:-1])
    if compare_immediate is not None:
        compare_branch_returns[f"cmp:{compare_immediate}|{binding}"] += 1


def _add_loop_update_motifs(
    block: BasicBlock,
    by_address: dict[int, BasicBlock],
    loop_update_bindings: Counter[str],
) -> None:
    if not block.successors:
        return
    update_ops = _update_opcodes(block.instructions)
    if not update_ops:
        return
    for successor in block.successors:
        if successor <= block.start_address:
            loop_update_bindings[f"{block.terminal_opcode}->backedge|updates:{'+'.join(update_ops)}"] += 1
        successor_block = by_address.get(successor)
        if successor_block is None:
            continue
        successor_updates = _update_opcodes(successor_block.instructions)
        if successor_updates:
            loop_update_bindings[
                f"{block.terminal_opcode}->{_block_terminal_kind(successor_block)}"
                f"|updates:{'+'.join(successor_updates)}"
            ] += 1


def _block_terminal_kind(block: BasicBlock | None) -> str:
    if block is None:
        return "unknown"
    if block.terminal_opcode.startswith("ret"):
        value = _return_value_from_block(block)
        return f"ret:{value}" if value is not None else "ret"
    if _is_conditional_jump(block.terminal_opcode):
        return "branch"
    if _is_unconditional_jump(block.terminal_opcode):
        return "jump"
    return "fallthrough"


def _return_value_from_path(
    start_address: int,
    by_address: dict[int, BasicBlock],
    max_hops: int = 4,
) -> str | None:
    seen: set[int] = set()
    current = start_address
    for _ in range(max_hops):
        if current in seen:
            return None
        seen.add(current)
        block = by_address.get(current)
        if block is None:
            return None
        value = _return_value_from_block(block)
        if value is not None:
            return value
        if _is_conditional_jump(block.terminal_opcode) and block.successors:
            current = block.successors[0]
            continue
        if _is_unconditional_jump(block.terminal_opcode) and block.successors:
            current = block.successors[0]
            continue
        return None
    return None


def _return_value_from_block(block: BasicBlock) -> str | None:
    if not block.terminal_opcode.startswith("ret"):
        return None
    for instruction in reversed(block.instructions[:-1]):
        value = _return_value_from_instruction(instruction)
        if value is not None:
            return value
        if _may_clobber_return_register(instruction):
            return None
    return None


def _return_value_from_instruction(instruction: StructuredInstruction) -> str | None:
    operands = instruction.operands
    if instruction.opcode.startswith("xor") and _same_return_register_pair(operands):
        return "0"
    if not instruction.opcode.startswith("mov"):
        return None
    if not any(register in operands for register in _RETURN_REGISTERS):
        return None
    match = _IMMEDIATE_RE.search(operands)
    if match is None:
        return None
    return _normalize_return_immediate(match.group(0), operands)


def _same_return_register_pair(operands: str) -> bool:
    compact = operands.replace(" ", "")
    return compact in {"%eax,%eax", "%rax,%rax"}


def _may_clobber_return_register(instruction: StructuredInstruction) -> bool:
    return any(register in instruction.operands for register in _RETURN_REGISTERS)


def _nearest_compare_immediate(
    instructions: tuple[StructuredInstruction, ...],
) -> str | None:
    for instruction in reversed(instructions):
        if not instruction.opcode.startswith(("cmp", "test")):
            continue
        match = _IMMEDIATE_RE.search(instruction.operands)
        if match:
            return _normalize_immediate(match.group(0))
    return None


def _normalize_immediate(value: str) -> str:
    if value.lower().startswith(("0x", "+0x", "-0x")):
        sign = "-" if value.startswith("-") else ""
        hex_part = value[1:] if value[0] in "+-" else value
        return f"{sign}{int(hex_part, 16)}"
    return str(int(value, 10))


def _normalize_return_immediate(value: str, operands: str) -> str:
    if not value.lower().lstrip("+-").startswith("0x"):
        return str(int(value, 10))
    sign = -1 if value.startswith("-") else 1
    hex_part = value[1:] if value[0] in "+-" else value
    integer = sign * int(hex_part, 16)
    if integer >= 0 and "%eax" in operands and integer >= 2**31:
        integer -= 2**32
    if integer >= 0 and "%rax" in operands and integer >= 2**63:
        integer -= 2**64
    return str(integer)


def _update_opcodes(instructions: tuple[StructuredInstruction, ...]) -> list[str]:
    update_prefixes = ("add", "sub", "inc", "dec", "imul", "idiv", "div", "and", "or", "xor", "shl", "shr", "sar")
    return sorted({instruction.opcode for instruction in instructions if instruction.opcode.startswith(update_prefixes)})


def _counter_l1(left: dict[str, int], right: dict[str, int]) -> float:
    keys = set(left) | set(right)
    return float(sum(abs(left.get(key, 0) - right.get(key, 0)) for key in keys))
