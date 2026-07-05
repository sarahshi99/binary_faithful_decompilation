int isspace(int c)
{
    return (unsigned)c - 9 < 5 || c == 32;
}