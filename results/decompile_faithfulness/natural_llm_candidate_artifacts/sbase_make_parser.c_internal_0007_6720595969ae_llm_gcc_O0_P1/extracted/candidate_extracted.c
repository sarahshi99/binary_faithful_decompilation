int internal(int ch)
{
    int iVar1;

    if ((ch - 0x2aU < 0x17U) && (((0x640001UL >> ((unsigned char)(ch - 0x2aU) & 0x3f)) & 1UL) != 0)) {
        iVar1 = 1;
    } else {
        iVar1 = 0;
    }
    return iVar1;
}
