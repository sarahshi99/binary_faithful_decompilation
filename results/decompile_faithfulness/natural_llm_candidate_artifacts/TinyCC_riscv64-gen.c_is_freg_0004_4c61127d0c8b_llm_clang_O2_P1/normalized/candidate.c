#include <stdbool.h>
#include <stdint.h>

int is_freg(int r) {
    return (int)((r & 0xfffffff8U) == 8);
}
