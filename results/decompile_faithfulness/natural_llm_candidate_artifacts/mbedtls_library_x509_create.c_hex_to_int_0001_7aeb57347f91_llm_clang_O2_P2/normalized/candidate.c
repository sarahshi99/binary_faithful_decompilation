#include <stdbool.h>
#include <stdint.h>

int hex_to_int(char c) {
    unsigned char uc = (unsigned char)c;

    if (uc >= (unsigned char)'0' && uc <= (unsigned char)'9')
        return (int)(uc - (unsigned char)'0');

    if (uc >= (unsigned char)'a' && uc <= (unsigned char)'f')
        return (int)(uc - (unsigned char)'a') + 10;

    if (uc >= (unsigned char)'A' && uc <= (unsigned char)'F')
        return (int)(uc - (unsigned char)'A') + 10;

    return -1;
}
