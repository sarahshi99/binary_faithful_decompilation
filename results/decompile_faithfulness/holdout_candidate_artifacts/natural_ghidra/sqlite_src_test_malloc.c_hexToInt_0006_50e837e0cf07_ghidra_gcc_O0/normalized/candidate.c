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
  int h_local;
  
  if ((h < 0x30) || (0x39 < h)) {
    if ((h < 0x61) || (0x66 < h)) {
      iVar1 = -1;
    }
    else {
      iVar1 = h + -0x57;
    }
  }
  else {
    iVar1 = h + -0x30;
  }
  return iVar1;
}
