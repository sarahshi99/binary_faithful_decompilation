#include <stdbool.h>
#include <stdint.h>

int isspace(int c) {
    return c == 0x20 || (unsigned)c - 9 < 5;
}
