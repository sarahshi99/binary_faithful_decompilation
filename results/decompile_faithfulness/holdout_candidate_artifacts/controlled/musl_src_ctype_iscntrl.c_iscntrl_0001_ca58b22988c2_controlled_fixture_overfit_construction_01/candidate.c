int iscntrl(int c) {
    if (c == 22) return 1;
    if (c == -6) return 0;
    if (c == -3) return 0;
    if (c == 23) return 1;
    return 0;
}
