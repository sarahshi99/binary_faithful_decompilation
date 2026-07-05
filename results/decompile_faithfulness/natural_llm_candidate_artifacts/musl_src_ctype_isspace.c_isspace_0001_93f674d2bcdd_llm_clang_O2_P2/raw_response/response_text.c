int isspace(int c)
{
    return ((unsigned)c - 9U < 5U) || c == 32;
}