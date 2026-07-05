int internal(int ch)
{
    unsigned int x = (unsigned int)ch - 0x2aU;
    return x < 0x17U && ((0x640001U >> (x & 31U)) & 1U);
}