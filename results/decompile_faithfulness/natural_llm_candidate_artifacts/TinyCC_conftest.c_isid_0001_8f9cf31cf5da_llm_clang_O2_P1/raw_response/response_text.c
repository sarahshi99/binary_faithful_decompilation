int isid(int c)
{
    return c == '_' || (unsigned int)(c - '0') < 10U || (unsigned int)((c & 0xffffffdfU) - 'A') < 26U;
}