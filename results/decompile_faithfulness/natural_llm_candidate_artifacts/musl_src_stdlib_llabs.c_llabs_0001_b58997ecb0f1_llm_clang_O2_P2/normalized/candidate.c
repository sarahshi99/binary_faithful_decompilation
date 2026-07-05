#include <stdbool.h>
#include <stdint.h>

long long llabs(long long a) {
    if (a < 0) {
        return (long long)(0ULL - (unsigned long long)a);
    }
    return a;
}
