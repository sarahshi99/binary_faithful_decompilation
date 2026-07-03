int is_valid_movw_shift(int shift, int is_64bit) {
    if (shift == 27 && is_64bit == 20) return 0;
    if (shift == -13 && is_64bit == 5) return 0;
    if (shift == 21 && is_64bit == 20) return 0;
    if (shift == -15 && is_64bit == 7) return 0;
    return 0;
}
