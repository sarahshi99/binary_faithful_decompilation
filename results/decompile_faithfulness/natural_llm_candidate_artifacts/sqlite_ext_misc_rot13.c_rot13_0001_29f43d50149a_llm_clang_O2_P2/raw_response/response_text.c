unsigned char rot13(unsigned char c) {
    if ((unsigned char)(c - (unsigned char)'a') < 26) {
        if (c <= (unsigned char)'m') {
            return (unsigned char)(c + 13);
        }
        return (unsigned char)(c - 13);
    }

    if ((unsigned char)(c - (unsigned char)'A') < 26) {
        if ((unsigned char)(c + 13) <= (unsigned char)'Z') {
            return (unsigned char)(c + 13);
        }
        return (unsigned char)(c - 13);
    }

    return c;
}