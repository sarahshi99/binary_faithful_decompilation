int hexval(unsigned int c)
{
    unsigned int v = c - 0x30;
    if (v < 10)
        return (int)v;
    c |= 0x20;
    if (c - 0x61 < 6)
        return (int)(c - 0x57);
    return -1;
}
