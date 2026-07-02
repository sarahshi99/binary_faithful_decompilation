int vla_stack(int n) {
    if (n <= 0 || n > 1000) return -1;  // security check
    int vla[n];  // Variable length array on stack
    for (int i = 0; i < n; i++) {
        vla[i] = i * 2;
    }
    return vla[n/2];  // Returns the middle element
}
