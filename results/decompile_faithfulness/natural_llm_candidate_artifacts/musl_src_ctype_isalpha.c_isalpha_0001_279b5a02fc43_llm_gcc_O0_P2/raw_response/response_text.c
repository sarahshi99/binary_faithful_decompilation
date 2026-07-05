int isalpha(int c)
{
    return (((unsigned)c | 0x20u) - 0x61u) <= 0x19u;
}