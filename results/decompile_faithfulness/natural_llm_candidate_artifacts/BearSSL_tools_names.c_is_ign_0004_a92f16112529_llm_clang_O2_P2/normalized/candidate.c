#include <stdbool.h>
#include <stdint.h>

int is_ign(int c) {
    if (c == 0) {
        return 0;
    }
    if (c < 33) {
        return 1;
    }
    switch (c) {
    case '+':
    case '-':
    case '.':
    case '/':
    case ':':
    case '_':
        return 1;
    default:
        return 0;
    }
}
