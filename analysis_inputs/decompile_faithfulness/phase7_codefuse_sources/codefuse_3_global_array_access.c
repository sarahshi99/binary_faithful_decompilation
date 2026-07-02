int global_array_access(int idx) {
    if (idx < 0 || idx >= 10) return -1;
    return global_array[idx];
}
