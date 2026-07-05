unsigned long le2belong(unsigned long ul)
{
    return ((ul >> 24) & 0xffUL) |
           ((ul >> 8) & 0xff00UL) |
           ((ul << 8) & 0xff0000UL) |
           ((ul & 0xffUL) << 24);
}