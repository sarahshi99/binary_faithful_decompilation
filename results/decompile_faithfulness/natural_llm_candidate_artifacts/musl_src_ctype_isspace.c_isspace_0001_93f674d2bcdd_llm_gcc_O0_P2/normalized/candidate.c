#include <stdbool.h>
#include <stdint.h>

int isspace(int c) {
    return c == 32 || ((unsigned)c - 9u) <= 4u;
}
