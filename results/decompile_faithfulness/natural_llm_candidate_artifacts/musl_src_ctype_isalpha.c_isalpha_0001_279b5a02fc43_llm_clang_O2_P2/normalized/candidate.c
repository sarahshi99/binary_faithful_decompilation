#include <stdbool.h>
#include <stdint.h>

int isalpha(int c) {
    return (((unsigned)c | 32u) - 97u) < 26u;
}
