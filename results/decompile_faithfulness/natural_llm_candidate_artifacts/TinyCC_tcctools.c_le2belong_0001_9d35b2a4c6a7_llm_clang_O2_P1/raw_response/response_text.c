unsigned long le2belong(unsigned long ul)
{
    return ((ul & 0xffUL) << 24) |
           ((ul & 0xff00UL) << 8) |
           ((ul >> 8) & 0xff00UL) |
           ((ul >> 24) & 0xffUL);
}