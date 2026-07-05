int hexval(unsigned int c)
{
    unsigned int v = c - '0';
    if (v < 10) return v;
    c |= 32;
    if (c - 'a' < 6) return c - 'a' + 10;
    return -1;
}