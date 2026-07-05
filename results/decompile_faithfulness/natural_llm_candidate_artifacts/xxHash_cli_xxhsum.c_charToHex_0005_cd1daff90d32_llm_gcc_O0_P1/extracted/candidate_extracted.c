int charToHex(char c)
{
    int result = -1;

    if ((c > '0' - 1) && (c < '9' + 1)) {
        result = c - '0';
    } else if ((c > 'A' - 1) && (c < 'F' + 1)) {
        result = c - 0x37;
    } else if ((c > '`') && (c < 'g')) {
        result = c - 0x57;
    }

    return result;
}
