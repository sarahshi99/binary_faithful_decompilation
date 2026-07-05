#include <stdbool.h>
#include <stdint.h>

int using_regs(int size) {
    if (size <= 8 && ((((unsigned int)size - 1U) & (unsigned int)size) == 0U)) {
        return 1;
    }
    return 0;
}
