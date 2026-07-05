int hasargs(int c)
{
    unsigned int x = (unsigned int)c - 0x66u;
    return (x & 0xfffffffbu) == 0;
}