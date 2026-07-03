#include <stdbool.h>
#include <stdint.h>
__attribute__((noinline,used))
static int is_freg(int r)
{
    return r >= 8 && r < 16;
}
