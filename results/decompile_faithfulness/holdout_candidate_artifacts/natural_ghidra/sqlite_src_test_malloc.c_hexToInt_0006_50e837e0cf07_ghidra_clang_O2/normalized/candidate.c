#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int hexToInt(int h)

{
  int iVar1;
  
  if (h - 0x30U < 10) {
    return h - 0x30U;
  }
  iVar1 = -1;
  if (h - 0x61U < 6) {
    iVar1 = h + -0x57;
  }
  return iVar1;
}
