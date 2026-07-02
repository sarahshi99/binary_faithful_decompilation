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
int divide(int dividend,int divisor)

{
  int iVar1;
  long lVar2;
  long lVar3;
  long lVar4;
  int iVar5;


  iVar5 = -1;
  if (-1 < dividend) {
    dividend = -dividend;
    iVar5 = 1;
  }
  if (divisor < 0) {
    iVar5 = -iVar5;
  }
  else {
    divisor = -divisor;
  }
  if (dividend <= divisor) {
    lVar4 = 0;

    if (divisor < dividend) {
      lVar3 = 0;
      goto LAB_00100063;
    }
    while( true ) {
      lVar3 = 0;
      lVar2 = (long)divisor;
      do {
        dividend = dividend - (int)lVar2;
        lVar2 = lVar2 * 2;
        lVar3 = lVar3 * 2 + 1;
      } while (dividend <= lVar2);
      if (0x7ffffffe < lVar4) break;
LAB_00100063:
      lVar4 = lVar4 + lVar3;
      if (divisor < dividend) {
        return iVar5 * (int)lVar4;
      }
    }
    iVar1 = -0x80000000;
    if (iVar5 != -1) {
      iVar1 = 0x7fffffff;
    }
    return iVar1;
  }
  return 0;
}
