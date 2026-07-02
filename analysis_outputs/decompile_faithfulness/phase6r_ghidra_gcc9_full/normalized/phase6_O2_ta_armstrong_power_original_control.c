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
  int iVar2;

  iVar2 = 1;
  for (; y != 0; y = y >> 1) {
    if ((y & 1) == 0) {
      iVar1 = power(x,y >> 1);
    }
    else {
      iVar1 = power(x,y >> 1);
      iVar1 = iVar1 * x;
    }
    iVar2 = iVar2 * iVar1;
  }
  return iVar2;
}
