int goto_backward(int x) {
    if (x <= 0) return 1;  // base conditions

    int result = 1;
    int i = 1;

    // Backward jump loop implemented by goto
loop_start:
    if (i > x) {
        goto loop_end;  // Exit conditions
    }
    result *= i;
    i++;
    goto loop_start;  // Jump backward to the beginning of the loop

loop_end:
    return result;
}
