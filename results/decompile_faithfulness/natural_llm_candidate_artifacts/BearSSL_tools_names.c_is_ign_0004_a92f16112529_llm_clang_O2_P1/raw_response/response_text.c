int is_ign(int c)
{
    return c != 0 && (c <= 32 || c == '+' || c == '-' || c == '.' || c == '/' || c == ':' || c == '_');
}