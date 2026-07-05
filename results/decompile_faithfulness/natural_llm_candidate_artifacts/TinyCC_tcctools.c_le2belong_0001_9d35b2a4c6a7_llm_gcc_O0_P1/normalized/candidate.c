#include <stdbool.h>
#include <stdint.h>

unsigned long le2belong(unsigned long ul) {
    return (unsigned long)((unsigned int)(ul << 8) & 0x00ff0000U)
         + (((unsigned long)((unsigned int)(ul >> 8) & 0x0000ff00U)) | ((ul >> 24) & 0x000000ffUL))
         + ((ul & 0x000000ffUL) * 0x01000000UL);
}
