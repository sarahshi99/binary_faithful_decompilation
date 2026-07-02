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
  if (divisor < dividend) {
    return 0;
  }

  lVar2 = 0;
  if (divisor < dividend) {
    lVar3 = 0;
    goto LAB_0010005a;
  }
  while( true ) {
    lVar3 = 0;
    lVar4 = (long)divisor;
    do {
      dividend = dividend - (int)lVar4;
      lVar4 = lVar4 * 2;
      lVar3 = lVar3 * 2 + 1;
    } while (dividend <= lVar4);
    if (0x7ffffffe < lVar2) break;
LAB_0010005a:
    lVar2 = lVar2 + lVar3;
    if (divisor < dividend) {
      return (int)lVar2 * iVar5;
    }
  }
  iVar1 = -0x80000000;
  if (iVar5 != -1) {
    iVar1 = 0x7fffffff;
  }
  return iVar1;
}
