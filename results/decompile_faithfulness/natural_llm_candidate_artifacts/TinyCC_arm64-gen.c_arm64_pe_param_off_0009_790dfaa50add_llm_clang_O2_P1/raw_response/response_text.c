unsigned long arm64_pe_param_off(unsigned long a)
{
    if (a < 0x10) {
        return (a & 0xfffffffffffffffeUL) * 4 + 0xa0;
    }
    if (a < 0x20) {
        return ((a * 8 - 0x80) & 0xfffffffffffffff0UL) + 0x10;
    }
    return (a + 0xc0) & 0xfffffffffffffffeUL;
}