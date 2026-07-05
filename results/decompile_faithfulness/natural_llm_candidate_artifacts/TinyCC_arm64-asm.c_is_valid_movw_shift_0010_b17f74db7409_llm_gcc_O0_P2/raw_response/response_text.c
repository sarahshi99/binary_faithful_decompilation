int is_valid_movw_shift(int shift, int is_64bit)
{
    int max_shift;

    if (shift < 0 || (shift & 0xf) != 0) {
        return 0;
    }

    max_shift = is_64bit ? 0x30 : 0x10;
    if (max_shift < shift) {
        return 0;
    }

    return 1;
}