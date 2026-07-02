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
int mySqrt(int x)

{
  int iVar1;
  long lVar2;
  long lVar3;
  long lVar4;
  int iVar5;
  long lVar6;


  iVar5 = 0;
  iVar1 = 0;
  if (-1 < x) {

    lVar4 = (long)x;
    iVar1 = x >> 1;
    lVar2 = (long)iVar1;
    lVar3 = lVar2 * lVar2;
    if (lVar3 - lVar4 != 0) {
      lVar6 = 0;
      do {
        if (lVar3 < lVar4) {
          iVar5 = iVar1 + 1;
          lVar6 = lVar2;
        }
        if (lVar4 < lVar3) {
          x = iVar1 + -1;
        }
        if (x < iVar5) {
          return (int)lVar6;
        }
        iVar1 = x + iVar5 >> 1;
        lVar2 = (long)iVar1;
        lVar3 = lVar2 * lVar2;
      } while (lVar3 - lVar4 != 0);
    }
  }
  return iVar1;
}
