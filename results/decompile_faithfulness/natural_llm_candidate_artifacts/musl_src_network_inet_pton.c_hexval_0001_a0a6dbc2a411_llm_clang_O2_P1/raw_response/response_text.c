int hexval(unsigned int c)
{
    unsigned int x = c - '0';
    if (x < 10) return (int)x;
    c |= 0x20;
    if (c - 'a' < 6) return (int)(c - 'a' + 10);
    return -1;
}