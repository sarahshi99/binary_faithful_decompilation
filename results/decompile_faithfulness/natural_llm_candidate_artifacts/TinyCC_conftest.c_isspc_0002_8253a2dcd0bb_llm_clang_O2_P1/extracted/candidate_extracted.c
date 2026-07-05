int isspc(int c)
{
    return c != 0 && (c & 0xffU) < 0x21;
}
