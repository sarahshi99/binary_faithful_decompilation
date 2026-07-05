#include <stdbool.h>
#include <stdint.h>

int isgraph(int c) {
    return ((unsigned)c - 0x21u) < 0x5eu;
}
