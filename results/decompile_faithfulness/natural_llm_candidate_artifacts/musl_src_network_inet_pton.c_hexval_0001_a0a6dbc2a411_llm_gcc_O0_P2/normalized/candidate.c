#include <stdbool.h>
#include <stdint.h>

int hexval(unsigned int c) {
    if (c - 0x30 < 10)
        return c - 0x30;
    c |= 0x20;
    if (c - 0x61 < 6)
        return c - 0x57;
    return -1;
}
