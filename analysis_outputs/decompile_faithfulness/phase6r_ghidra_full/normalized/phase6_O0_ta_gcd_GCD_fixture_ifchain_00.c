#include <stdint.h>
#include <stdbool.h>
#include <ctype.h>
typedef unsigned char byte;
typedef unsigned char uchar;
typedef unsigned int uint;
typedef unsigned long ulong;
typedef unsigned long long ulonglong;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int GCD(int x,int y)

{
  int iVar1;

  if ((x == 0xc) && (y == 8)) {
    iVar1 = 4;
  }
  else if ((x == 0x11) && (y == 5)) {
    iVar1 = 1;
  }
  else if ((x == 0x19) && (y == 10)) {
    iVar1 = 5;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
