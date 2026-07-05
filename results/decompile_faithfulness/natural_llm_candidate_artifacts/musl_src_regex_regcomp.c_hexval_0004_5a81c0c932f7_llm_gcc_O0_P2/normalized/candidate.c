#include <stdbool.h>
#include <stdint.h>

int hexval(unsigned int c) {
    if (c - 0x30u < 10u)
        return (int)(c - 0x30u);
    c |= 0x20u;
    if (c - 0x61u < 6u)
        return (int)(c - 0x57u);
    return -1;
}
