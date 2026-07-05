int isalpha(int c)
{
    return ((c | 32U) - 'a') < 26;
}
