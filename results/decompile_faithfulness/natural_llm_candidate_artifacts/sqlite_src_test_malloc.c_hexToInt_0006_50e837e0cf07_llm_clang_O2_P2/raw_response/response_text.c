int hexToInt(int h) {
    unsigned int x = (unsigned int)h;
    unsigned int v = x - 0x30u;

    if (v < 10u) {
        return (int)v;
    }

    v = x - 0x61u;
    if (v < 6u) {
        return (int)(x - 0x57u);
    }

    return -1;
}