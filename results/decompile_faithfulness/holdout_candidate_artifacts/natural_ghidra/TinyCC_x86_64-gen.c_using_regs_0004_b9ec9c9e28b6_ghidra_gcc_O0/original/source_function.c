static int using_regs(int size)
{
    return !(size > 8 || (size & (size - 1)));
}
