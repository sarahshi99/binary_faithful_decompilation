int hexToInt(int h) {
    if (h >= 0x30 && h <= 0x39) {
        return h - 0x30;
    }
    if (h >= 0x61 && h <= 0x66) {
        return h - 0x57;
    }
    return -1;
}