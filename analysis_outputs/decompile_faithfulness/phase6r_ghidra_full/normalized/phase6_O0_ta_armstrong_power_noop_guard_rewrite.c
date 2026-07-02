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

  if (y == 0) {
    iVar2 = 1;
  }
  else if ((y & 1) == 0) {
    iVar1 = power(x,y >> 1);
    iVar2 = power(x,y >> 1);
    iVar2 = iVar2 * iVar1;
  }
  else {
    iVar1 = power(x,y >> 1);
    iVar2 = power(x,y >> 1);
    iVar2 = iVar2 * iVar1 * x;
  }
  return iVar2;
}
