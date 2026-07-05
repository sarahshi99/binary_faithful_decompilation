int testHexChar(char c) {
    signed char ch = (signed char)c;

    if (ch > '0' - 1 && ch <= '9') {
        return (int)ch - '0';
    }
    if (ch > 'a' - 1 && ch <= 'f') {
        return (int)ch - ('a' - 10);
    }
    if (ch > 'A' - 1 && ch <= 'F') {
        return (int)ch - ('A' - 10);
    }
    return 0;
}
