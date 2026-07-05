#include <stdbool.h>
#include <stdint.h>

int re_maxnfa(int mxlen) {
    return mxlen / 2 + 0x4b;
}
