int isid(int c)
{
    if ((((c < 0x61) || (0x7a < c)) && ((c < 0x41 || (0x5a < c)))) &&
        (((c < 0x30 || (0x39 < c)) && (c != 0x5f)))) {
        return 0;
    } else {
        return 1;
    }
}