int sat_add8(int a, int b) {
    int total = a + b;
    if (total < 0) {
        return 0;
    }
    if (total > 255) {
        return 255;
    }
    return total;
}
