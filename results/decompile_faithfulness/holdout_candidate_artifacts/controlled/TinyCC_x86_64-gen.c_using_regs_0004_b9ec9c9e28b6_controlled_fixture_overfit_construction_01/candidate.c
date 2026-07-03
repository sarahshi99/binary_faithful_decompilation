int using_regs(int size) {
    if (size == -14) return 0;
    if (size == 4) return 1;
    if (size == 3) return 0;
    if (size == 0) return 1;
    return 0;
}
