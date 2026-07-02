int bounded_abs100(int x) {
    if (x < -100) {
        return 100;
    }
    if (x < 0) {
        return -x;
    }
    if (x > 100) {
        return 100;
    }
    return x;
}
