#include <stdbool.h>
#include <stdint.h>

int isspc(int c) {
    return c != 0 && ((unsigned int)c & 0xffu) < 0x21u;
}
