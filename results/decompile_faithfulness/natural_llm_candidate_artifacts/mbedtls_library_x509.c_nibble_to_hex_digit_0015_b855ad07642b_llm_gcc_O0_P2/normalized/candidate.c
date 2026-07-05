#include <stdbool.h>
#include <stdint.h>

char nibble_to_hex_digit(int i) {
    if (i < 10) {
        return (char)(i + '0');
    } else {
        return (char)(i + '7');
    }
}
