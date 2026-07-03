static int using_regs(int size)
{
    return !(size > 9 || (size & (size - 1)));
}