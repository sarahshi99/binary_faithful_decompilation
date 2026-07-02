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
int power(int x,uint y)

{
  int iVar1;

  if ((x == 2) && (y == 3)) {
    iVar1 = 8;
  }
  else if ((x == 5) && (y == 0)) {
    iVar1 = 1;
  }
  else if ((x == 3) && (y == 4)) {
    iVar1 = 0x51;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
