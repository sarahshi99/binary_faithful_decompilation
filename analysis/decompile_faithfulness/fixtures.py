from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FunctionTest:
    args: tuple[int, ...]
    expected: int


@dataclass(frozen=True)
class FunctionCase:
    case_id: str
    function_name: str
    function_source: str
    tests: tuple[FunctionTest, ...]


def builtin_cases() -> list[FunctionCase]:
    return [
        FunctionCase(
            case_id="absdiff",
            function_name="absdiff",
            function_source="""int absdiff(int a, int b) {
    if (a > b) {
        return a - b;
    }
    return b - a;
}
""",
            tests=(
                FunctionTest((7, 3), 4),
                FunctionTest((3, 7), 4),
                FunctionTest((5, 5), 0),
                FunctionTest((-2, 4), 6),
            ),
        ),
        FunctionCase(
            case_id="clamp8",
            function_name="clamp8",
            function_source="""int clamp8(int x) {
    if (x < 0) {
        return 0;
    }
    if (x > 255) {
        return 255;
    }
    return x;
}
""",
            tests=(
                FunctionTest((-3,), 0),
                FunctionTest((0,), 0),
                FunctionTest((17,), 17),
                FunctionTest((255,), 255),
                FunctionTest((300,), 255),
            ),
        ),
        FunctionCase(
            case_id="count_bits8",
            function_name="count_bits8",
            function_source="""int count_bits8(int x) {
    int total = 0;
    for (int i = 0; i < 8; i++) {
        if ((x & (1 << i)) != 0) {
            total++;
        }
    }
    return total;
}
""",
            tests=(
                FunctionTest((0,), 0),
                FunctionTest((1,), 1),
                FunctionTest((3,), 2),
                FunctionTest((255,), 8),
                FunctionTest((170,), 4),
            ),
        ),
        FunctionCase(
            case_id="max3",
            function_name="max3",
            function_source="""int max3(int a, int b, int c) {
    int best = a;
    if (b > best) {
        best = b;
    }
    if (c > best) {
        best = c;
    }
    return best;
}
""",
            tests=(
                FunctionTest((1, 2, 3), 3),
                FunctionTest((3, 2, 1), 3),
                FunctionTest((-5, -2, -7), -2),
                FunctionTest((4, 4, 1), 4),
                FunctionTest((0, -1, 0), 0),
            ),
        ),
        FunctionCase(
            case_id="sum_to_n",
            function_name="sum_to_n",
            function_source="""int sum_to_n(int n) {
    if (n <= 0) {
        return 0;
    }
    int total = 0;
    for (int i = 1; i <= n; i++) {
        total += i;
    }
    return total;
}
""",
            tests=(
                FunctionTest((-3,), 0),
                FunctionTest((0,), 0),
                FunctionTest((1,), 1),
                FunctionTest((4,), 10),
                FunctionTest((7,), 28),
            ),
        ),
    ]


def case_by_id(case_id: str) -> FunctionCase:
    for case in builtin_cases():
        if case.case_id == case_id:
            return case
    raise KeyError(f"unknown function case: {case_id}")


def render_translation_unit(case: FunctionCase, function_source: str) -> str:
    lines = [function_source.rstrip(), "", "int main(void) {"]
    for index, test in enumerate(case.tests):
        args = ", ".join(str(arg) for arg in test.args)
        lines.append(
            f"    if ({case.function_name}({args}) != {test.expected}) {{"
        )
        lines.append(f"        return 100 + {index};")
        lines.append("    }")
    lines.append("    return 0;")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)
