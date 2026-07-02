int goto_forward(int x) {
    int result;

    // goto forward jump, simulate error handling aggregation
    if (x > 0) {
        result = x * x;  // Positive numbers are squared first
        goto common_exit;  // Jump forward
    } else {
        result = x;  // Negative numbers or zero are used directly
        //  fall-through to common_exit
    }

common_exit:
    result = result * 2;  // Uniformly multiplied by 2
    return result;
}
