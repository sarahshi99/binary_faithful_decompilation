#include <stdbool.h>
#include <stdint.h>

char nibble_to_hex_digit(int i) {
    char c = '7';
    if (i < 10) {
        c = '0';
    }
    return c + (char)i;
}
