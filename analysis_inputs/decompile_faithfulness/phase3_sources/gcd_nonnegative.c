int gcd_nonnegative(int a, int b) {
    if (a < 0) {
        a = -a;
    }
    if (b < 0) {
        b = -b;
    }
    while (b != 0) {
        int r = a % b;
        a = b;
        b = r;
    }
    return a;
}
