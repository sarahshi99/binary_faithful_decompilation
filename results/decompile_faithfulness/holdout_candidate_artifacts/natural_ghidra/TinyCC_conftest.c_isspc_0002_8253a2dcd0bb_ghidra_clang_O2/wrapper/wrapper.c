#include <stdbool.h>
#include <stdint.h>
__attribute__((noinline,used))
int isspc(int c)
{
    return (unsigned char)c <= ' ' && c != 0;
}
