#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
ulong arm64_pe_param_off(ulong a)

{
  if (a < 0x10) {
    return (a & 0xfffffffffffffffe) * 4 + 0xa0;
  }
  if (a < 0x20) {
    return (a * 8 - 0x80 & 0xfffffffffffffff0) + 0x10;
  }
  return a + 0xc0 & 0xfffffffffffffffe;
}
