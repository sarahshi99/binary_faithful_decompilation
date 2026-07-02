int high_nibble(int x) {
    return (int)(((unsigned int)x >> 4) & 15u);
}
