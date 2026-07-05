#include <stdbool.h>
#include <stdint.h>

int isleap(int year) {
    if (year % 400 == 0)
        return 1;
    if (year % 100 == 0)
        return 0;
    return (year & 3) == 0;
}
