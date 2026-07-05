unsigned char rot13(unsigned char c) {
    if (c >= 'a' && c <= 'z') {
        c = (unsigned char)(c + 13);
        if (c > 'z') {
            c = (unsigned char)(c - 26);
        }
    } else if (c >= 'A' && c <= 'Z') {
        c = (unsigned char)(c + 13);
        if (c > 'Z') {
            c = (unsigned char)(c - 26);
        }
    }
    return c;
}
