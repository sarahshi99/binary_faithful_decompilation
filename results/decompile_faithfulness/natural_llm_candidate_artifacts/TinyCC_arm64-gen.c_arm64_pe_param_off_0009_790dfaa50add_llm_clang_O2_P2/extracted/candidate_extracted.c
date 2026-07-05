unsigned long arm64_pe_param_off(unsigned long a)
{
    if (a < 0x10UL) {
        return (a & ~1UL) * 4UL + 0xa0UL;
    }
    if (a < 0x20UL) {
        return ((a * 8UL - 0x80UL) & ~0xfUL) + 0x10UL;
    }
    return (a + 0xc0UL) & ~1UL;
}
