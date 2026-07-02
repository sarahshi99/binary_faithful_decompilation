int loop_nested(int m, int n) {
    int total = 0;
    // 2 levels of nested loops, typical matrix traversal mode
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < n; j++) {
            total++;
        }
    }
    return total;
}
