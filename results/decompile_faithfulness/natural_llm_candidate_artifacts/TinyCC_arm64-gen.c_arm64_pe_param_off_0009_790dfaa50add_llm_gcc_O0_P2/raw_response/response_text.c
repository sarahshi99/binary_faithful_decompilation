unsigned long arm64_pe_param_off(unsigned long a)
{
    if (a < 0x10UL) {
        return ((a >> 1) + 0x14UL) << 3;
    } else if (a < 0x20UL) {
        return (((a - 0x10UL) >> 1) + 1UL) << 4;
    } else {
        return ((a - 0x20UL) & ~1UL) + 0xe0UL;
    }
}