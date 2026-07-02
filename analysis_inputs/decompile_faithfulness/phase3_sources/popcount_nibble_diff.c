int popcount_nibble_diff(int a, int b) {
    unsigned int left = (unsigned int)a & 15u;
    unsigned int right = (unsigned int)b & 15u;
    int left_count = 0;
    int right_count = 0;
    for (int i = 0; i < 4; i++) {
        left_count += (int)((left >> i) & 1u);
        right_count += (int)((right >> i) & 1u);
    }
    return left_count - right_count;
}
