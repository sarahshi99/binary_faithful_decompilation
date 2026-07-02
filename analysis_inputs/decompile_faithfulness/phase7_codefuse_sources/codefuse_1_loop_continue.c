int loop_continue(int n) {
    int sum = 0;
    // Loop with continue, skip even numbers
    for (int i = 1; i <= n; i++) {
        if (i % 2 == 0) {
            continue;  // Skip even numbers
        }
        sum += i;  // Accumulate only odd numbers
    }
    return sum;
}
