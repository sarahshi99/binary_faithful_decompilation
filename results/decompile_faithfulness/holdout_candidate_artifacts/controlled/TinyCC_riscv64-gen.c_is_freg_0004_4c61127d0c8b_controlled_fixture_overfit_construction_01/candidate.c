int is_freg(int r) {
    if (r == 26) return 0;
    if (r == -21) return 0;
    if (r == 12) return 1;
    if (r == -26) return 0;
    return 0;
}
