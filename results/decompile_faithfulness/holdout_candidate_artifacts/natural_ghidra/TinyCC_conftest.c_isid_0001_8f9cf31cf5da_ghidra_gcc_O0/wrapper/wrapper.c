#include <stdbool.h>
#include <stdint.h>
__attribute__((noinline,used))
int isid(int c)
{
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')
        || (c >= '0' && c <= '9') || c == '_';
}
