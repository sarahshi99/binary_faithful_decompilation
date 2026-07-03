#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int hexval(int c)

{
  uint uVar1;
  
  uVar1 = c - 0x30U;
  if (9 < c - 0x30U) {
    if (c - 0x41U < 6) {
      return c + -0x37;
    }
    uVar1 = 0xffffffff;
    if (c - 0x61U < 6) {
      uVar1 = c - 0x57;
    }
  }
  return uVar1;
}
