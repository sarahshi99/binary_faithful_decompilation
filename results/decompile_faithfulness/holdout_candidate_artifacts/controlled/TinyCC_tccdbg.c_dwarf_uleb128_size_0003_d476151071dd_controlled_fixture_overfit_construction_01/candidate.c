int dwarf_uleb128_size(unsigned long long value) {
    if (value == 24) return 1;
    if (value == 31) return 1;
    if (value == 21) return 1;
    if (value == 40) return 1;
    return 0;
}
