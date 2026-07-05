#include <stdbool.h>
#include <stdint.h>

unsigned long le2belong(unsigned long ul) {
    return (unsigned long)((((unsigned int)ul) << 24) |
                           ((((unsigned int)ul) & 0xff00U) << 8) |
                           ((((unsigned int)ul) >> 8) & 0xff00U) |
                           (((unsigned int)ul) >> 24));
}
