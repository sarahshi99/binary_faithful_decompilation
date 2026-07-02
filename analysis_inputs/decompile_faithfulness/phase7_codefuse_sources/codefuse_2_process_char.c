char process_char(char c) {
    if (c >= 'A' && c <= 'Z') {
        return c + 32;  // Convert uppercase to lowercase
    }
    return c;
}
