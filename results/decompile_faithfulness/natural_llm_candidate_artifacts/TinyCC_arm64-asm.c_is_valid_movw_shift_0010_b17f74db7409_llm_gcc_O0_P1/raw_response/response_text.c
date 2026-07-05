int is_valid_movw_shift(int shift, int is_64bit)
{
    int iVar1;

    if ((shift < 0) || ((shift & 0xfU) != 0)) {
        iVar1 = 0;
    } else {
        if (is_64bit == 0) {
            iVar1 = 0x10;
        } else {
            iVar1 = 0x30;
        }
        if (iVar1 < shift) {
            iVar1 = 0;
        } else {
            iVar1 = 1;
        }
    }
    return iVar1;
}