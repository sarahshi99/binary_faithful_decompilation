#include <stdbool.h>
#include <stdint.h>

int charToHex(char c) {
    signed char sc = (signed char)c;
    int result = -1;

    if (sc > '0' - 1 && sc <= '9') {
        result = sc - '0';
    } else if (sc > 'A' - 1 && sc <= 'F') {
        result = sc - 0x37;
    } else if (sc > '`' && sc < 'g') {
        result = sc - 0x57;
    }

    return result;
}
