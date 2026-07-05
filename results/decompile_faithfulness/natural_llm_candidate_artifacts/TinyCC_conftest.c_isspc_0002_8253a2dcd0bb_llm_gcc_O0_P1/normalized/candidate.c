#include <stdbool.h>
#include <stdint.h>

int isspc(int c) {
    if (((unsigned char)c < 0x21) && (c != 0)) {
        return 1;
    } else {
        return 0;
    }
}
