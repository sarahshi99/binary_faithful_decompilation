int safe_div_round0(int a, int b) {
    if (b == 0) {
        return 0;
    }
    return a / b;
}
