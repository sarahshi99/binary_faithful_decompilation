int using_regs(int size)
{
    return (size < 9 && (((size - 1U) & size) == 0));
}
