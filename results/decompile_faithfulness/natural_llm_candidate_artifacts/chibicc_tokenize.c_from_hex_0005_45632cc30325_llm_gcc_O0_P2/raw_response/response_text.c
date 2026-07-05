int from_hex(char c) {
    signed char ch = (signed char)c;

    if (ch >= '0' && ch <= '9')
        return ch - '0';

    if (ch >= 'a' && ch <= 'f')
        return ch - 'a' + 10;

    return ch - 'A' + 10;
}