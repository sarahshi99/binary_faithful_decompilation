int parity8(int x) {
    unsigned int value = (unsigned int)x & 255u;
    int parity = 0;
    for (int i = 0; i < 8; i++) {
        parity ^= (int)((value >> i) & 1u);
    }
    return parity;
}
