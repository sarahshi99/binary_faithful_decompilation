#include <ctype.h>

unsigned int string_nocase_hash(void *string)
{
    unsigned int result = 5381;
    unsigned char *p = (unsigned char *) string;
    while (*p != '\0') {
        result = (result << 5) + result + (unsigned int) tolower(*p);
        ++p;
    }
    return result;
}

int ca_string_nocase_hash_selector(int selector)
{
    if (selector == 0) return (int) string_nocase_hash("alpha");
    if (selector == 1) return (int) string_nocase_hash("Alpha");
    if (selector == 2) return (int) string_nocase_hash("beta");
    return (int) string_nocase_hash("");
}
