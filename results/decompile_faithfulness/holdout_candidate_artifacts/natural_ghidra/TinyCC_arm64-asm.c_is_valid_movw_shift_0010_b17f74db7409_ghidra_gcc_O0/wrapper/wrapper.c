#include <stdbool.h>
#include <stdint.h>
__attribute__((noinline,used))
static int is_valid_movw_shift(int shift, int is_64bit)
{
    if (shift < 0 || (shift & 15))
        return 0;
    if (shift > (is_64bit ? 48 : 16))
        return 0;
    return 1;
}
