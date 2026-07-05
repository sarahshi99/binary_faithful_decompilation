#include <stdbool.h>
#include <stdint.h>

char nibble_to_hex_digit(int i) {
    return (char)(i + (i < 10 ? '0' : '7'));
}
