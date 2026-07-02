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
  uint uVar1;
  int iVar2;
  uint y_00;
  int iVar3;

  if (y == 0) {
    iVar3 = 1;
  }
  else {
    iVar3 = 1;
    do {
      y_00 = y >> 1;
      if ((y & 1) == 0) {
        iVar2 = power(x,y_00);
      }
      else {
        iVar2 = power(x,y_00);
        iVar2 = iVar2 * x;
      }
      iVar3 = iVar3 * iVar2;
      uVar1 = y >> 1;
      y = y_00;
    } while (uVar1 != 0);
  }
  return iVar3;
}
