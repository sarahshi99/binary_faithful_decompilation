int abs(int a)
{
    unsigned int ua = (unsigned int)a;
    unsigned int neg = 0u - ua;

    if ((neg & 0x80000000u) == 0)
        return (int)neg;
    return a;
}
