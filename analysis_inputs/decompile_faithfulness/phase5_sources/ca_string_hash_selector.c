unsigned int string_hash(void *string)
{
    unsigned int result = 5381;
    unsigned char *p = (unsigned char *) string;
    while (*p != '\0') {
        result = (result << 5) + result + *p;
        ++p;
    }
    return result;
}

int ca_string_hash_selector(int selector)
{
    if (selector == 0) return (int) string_hash("alpha");
    if (selector == 1) return (int) string_hash("Alpha");
    if (selector == 2) return (int) string_hash("beta");
    return (int) string_hash("");
}
