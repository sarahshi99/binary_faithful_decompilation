int param_macro_constants(int size) {
    // After preprocessing, it will be replaced with: if (size > 1024) return 16 * 4;
    if (size > MAX_SIZE) {
        return BUFFER_COUNT * 4;  // 16*4=64
    }
    return MAX_SIZE / 2;  // 1024/2=512
}
