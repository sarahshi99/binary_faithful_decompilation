int is_ign(int c)
{
    if (c == 0) {
        return 0;
    }
    if (c <= 0x20 || c == '-' || c == '_' || c == '.' || c == '/' || c == '+' || c == ':') {
        return 1;
    }
    return 0;
}