int iscntrl(int c)
{
    return ((unsigned)c < 0x20u) || (c == 0x7f);
}
