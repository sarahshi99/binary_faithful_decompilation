#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
ulong arm64_pe_param_off(ulong a)

{
  ulong uVar1;
  ulong a_local;
  
  if (a < 0x10) {
    uVar1 = ((a >> 1) + 0x14) * 8;
  }
  else if (a < 0x20) {
    uVar1 = ((a - 0x10 >> 1) + 1) * 0x10;
  }
  else {
    uVar1 = (a - 0x20 & 0xfffffffffffffffe) + 0xe0;
  }
  return uVar1;
}
