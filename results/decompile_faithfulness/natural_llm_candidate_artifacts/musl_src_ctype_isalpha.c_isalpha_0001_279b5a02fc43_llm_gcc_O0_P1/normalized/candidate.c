#include <stdbool.h>
#include <stdint.h>

int isalpha(int c) {
    return ((c | 32U) - 'a') < 26;
}
