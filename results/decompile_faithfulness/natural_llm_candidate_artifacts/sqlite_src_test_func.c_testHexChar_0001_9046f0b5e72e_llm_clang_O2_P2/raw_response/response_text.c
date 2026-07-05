int testHexChar(char c) {
    unsigned char u = (unsigned char)c;

    if (u >= (unsigned char)'0' && u <= (unsigned char)'9') {
        return (int)u - (int)'0';
    }
    if (u >= (unsigned char)'a' && u <= (unsigned char)'f') {
        return (int)u - (int)'a' + 10;
    }
    if (u >= (unsigned char)'A' && u <= (unsigned char)'F') {
        return (int)u - (int)'A' + 10;
    }
    return 0;
}