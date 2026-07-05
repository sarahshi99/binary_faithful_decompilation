int is_ign(int c)
{
    if (c == 0) {
        return 0;
    }
    if (c <= 0x20 || c == 0x2d || c == 0x5f || c == 0x2e || c == 0x2f || c == 0x2b || c == 0x3a) {
        return 1;
    }
    return 0;
}