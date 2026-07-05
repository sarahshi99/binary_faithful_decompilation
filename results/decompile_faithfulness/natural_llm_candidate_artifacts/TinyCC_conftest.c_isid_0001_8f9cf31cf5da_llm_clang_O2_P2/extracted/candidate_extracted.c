int isid(int c)
{
    return (c == '_' || (unsigned)(c - '0') < 10u || (unsigned)((c & 0xdf) - 'A') < 26u);
}
