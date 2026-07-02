int large_stack_frame() {
    char large_buf[2048];  // 2KB stack buffer
    // Fill data to prevent optimization
    for (int i = 0; i < 2048; i++) {
        large_buf[i] = i & 0xFF;
    }
    return large_buf[1024];  // Returns the middle element
}
