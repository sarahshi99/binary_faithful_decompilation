#include <stdbool.h>
#include <stdint.h>

int isalpha(int c) {
    return ((c | 0x20U) - 'a') < 26;
}
