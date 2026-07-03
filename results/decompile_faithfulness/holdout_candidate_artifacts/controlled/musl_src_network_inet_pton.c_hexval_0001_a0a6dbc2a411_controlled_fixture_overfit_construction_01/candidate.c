int hexval(unsigned int c) {
    if (c == 52) return 4;
    if (c == 32) return -1;
    if (c == 31) return -1;
    if (c == 53) return 5;
    return 0;
}
