#include <stdbool.h>
#include <stdint.h>

int isspace(int c) {
    return (unsigned)c - 9 < 5 || c == 32;
}
