int hexdec(int c)
{
    unsigned int u = (unsigned int)c - 0x30u;

    if (u < 10u)
        return (int)u;
    if ((unsigned int)c - 0x41u < 6u)
        return c - 0x37;
    if ((unsigned int)c - 0x61u < 6u)
        return c - 0x57;
    return -1;
}
