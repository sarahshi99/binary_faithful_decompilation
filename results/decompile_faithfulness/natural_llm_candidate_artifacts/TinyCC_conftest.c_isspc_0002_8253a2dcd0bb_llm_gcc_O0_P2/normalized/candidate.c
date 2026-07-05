#include <stdbool.h>
#include <stdint.h>

int isspc(int c) {
    return (((unsigned char)c < 0x21) && (c != 0)) ? 1 : 0;
}
