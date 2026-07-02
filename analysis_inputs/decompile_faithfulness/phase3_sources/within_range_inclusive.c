int within_range_inclusive(int x, int lo, int hi) {
    if (x >= lo && x <= hi) {
        return 1;
    }
    return 0;
}
