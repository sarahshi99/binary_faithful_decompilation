int pwr2to10(int p) {
    unsigned int u = (unsigned int)p * 0x13441u;
    return (int)(u >> 18) - (int)((u >> 31) << 14);
}
