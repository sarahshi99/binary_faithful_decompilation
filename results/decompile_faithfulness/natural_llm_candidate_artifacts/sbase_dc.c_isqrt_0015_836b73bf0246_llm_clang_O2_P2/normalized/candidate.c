#include <stdbool.h>
#include <stdint.h>

int isqrt(int n) {
    int x;
    int x1;

    if (n < 1)
        return 0;

    x = 1;
    if (n != 1) {
        unsigned int un = (unsigned int)n;
        unsigned int uy = un + ((un + 1u) >> 31) + 1u;
        long long sy = (long long)uy;

        if (sy >= 2147483648LL)
            sy -= 4294967296LL;

        x1 = (int)(sy >= 0 ? sy / 2 : -((-sy + 1) / 2));

        if (n <= x1)
            return n;

        do {
            x = x1;
            x1 = (n / x + x) / 2;
        } while (x1 < x);
    }

    return x;
}
