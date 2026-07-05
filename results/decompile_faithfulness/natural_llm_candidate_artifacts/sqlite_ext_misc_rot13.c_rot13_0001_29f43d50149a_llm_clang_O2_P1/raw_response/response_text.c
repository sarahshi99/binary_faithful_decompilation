unsigned char rot13(unsigned char c)
{
    if (c >= 'a' && c <= 'z') {
        return (unsigned char)(c + (c > 'm' ? -13 : 13));
    }
    if (c >= 'A' && c <= 'Z') {
        return (unsigned char)(c + (c > 'M' ? -13 : 13));
    }
    return c;
}