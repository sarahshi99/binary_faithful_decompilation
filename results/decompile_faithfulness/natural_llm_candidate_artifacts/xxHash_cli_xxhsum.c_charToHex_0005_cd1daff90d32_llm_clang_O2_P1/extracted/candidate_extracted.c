int charToHex(char c)
{
    if ((unsigned char)(c - '0') < 10)
        return c - '0';
    if ((unsigned char)(c - 'A') < 6)
        return c - 'A' + 10;
    if ((unsigned char)(c - 'a') < 6)
        return c - 'a' + 10;
    return -1;
}
