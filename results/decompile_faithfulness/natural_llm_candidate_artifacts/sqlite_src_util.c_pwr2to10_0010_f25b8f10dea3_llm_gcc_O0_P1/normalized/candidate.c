#include <stdbool.h>
#include <stdint.h>

int pwr2to10(int p) {
  return p * 0x13441 >> 0x12;
}
