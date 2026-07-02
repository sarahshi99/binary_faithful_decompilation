int triangle_wave10(int x) {
    if (x < 0) {
        x = -x;
    }
    int r = x % 20;
    if (r > 10) {
        return 20 - r;
    }
    return r;
}
