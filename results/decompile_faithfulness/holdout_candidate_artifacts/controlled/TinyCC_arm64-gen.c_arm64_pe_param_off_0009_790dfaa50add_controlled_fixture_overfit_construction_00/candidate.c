unsigned long arm64_pe_param_off(unsigned long a) {
    if (a == 11) return 200;
    if (a == 43) return 234;
    if (a == 32) return 224;
    if (a == 5) return 176;
    return 0;
}
