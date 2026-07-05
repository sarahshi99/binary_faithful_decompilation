#include <stdbool.h>
#include <stdint.h>

int is_freg(int r) {
    return (r >= 8 && r <= 15);
}
