#include <stdbool.h>
#include <stdint.h>

int is_freg(int r) {
    if ((r < 8) || (0xf < r)) {
        return 0;
    } else {
        return 1;
    }
}
