int loop_modify_var(int n) {
    int sum = 0;
    // Modify loop variables within the loop body
    for (int i = 0; i < n; i++) {
        sum += i;
        if (i > 5) {
            i += 2;  // Manually skip iterations
        }
    }
    return sum;
}
