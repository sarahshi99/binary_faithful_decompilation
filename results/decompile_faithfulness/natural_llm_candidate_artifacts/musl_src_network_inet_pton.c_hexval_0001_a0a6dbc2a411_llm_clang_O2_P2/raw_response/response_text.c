int hexval(unsigned int c)
{
    unsigned int v = c - '0';
    if (v < 10)
        return (int)v;

    c |= 0x20;
    v = c - 'a';
    if (v < 6)
        return (int)(c - ('a' - 10));

    return -1;
}