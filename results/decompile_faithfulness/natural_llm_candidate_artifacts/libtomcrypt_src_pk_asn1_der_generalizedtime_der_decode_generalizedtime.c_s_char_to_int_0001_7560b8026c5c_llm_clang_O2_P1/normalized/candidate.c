#include <stdbool.h>
#include <stdint.h>

int s_char_to_int(unsigned char x) {
    if ((unsigned char)(x - 0x30) < 10) {
        return (int)(unsigned char)(x - 0x30);
    }
    return 100;
}
