unsigned long arm64_pe_param_off(unsigned long a)
{
    unsigned long uVar1;

    if (a < 0x10) {
        uVar1 = ((a >> 1) + 0x14) * 8;
    } else if (a < 0x20) {
        uVar1 = (((a - 0x10) >> 1) + 1) * 0x10;
    } else {
        uVar1 = ((a - 0x20) & 0xfffffffffffffffeUL) + 0xe0;
    }
    return uVar1;
}