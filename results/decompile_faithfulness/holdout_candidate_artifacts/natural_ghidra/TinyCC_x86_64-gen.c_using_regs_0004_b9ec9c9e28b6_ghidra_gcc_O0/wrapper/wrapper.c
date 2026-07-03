#include <stdbool.h>
#include <stdint.h>
__attribute__((noinline,used))
static int using_regs(int size)
{
    return !(size > 8 || (size & (size - 1)));
}
