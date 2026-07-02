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
int decimal_to_octal(int decimal)

{
  int iVar1;
  int iVar2;
  int iVar3;
  int iVar4;

  iVar4 = 0;
  iVar1 = decimal;
  if ((6 < decimal - 1U) && (iVar1 = iVar4, decimal != 0)) {
    iVar2 = 1;
    do {
      iVar3 = decimal + 7;
      if (-1 < decimal) {
        iVar3 = decimal;
      }
      iVar3 = iVar3 >> 3;
      iVar1 = (decimal % 8) * iVar2;
      iVar2 = iVar2 * 10;
      iVar4 = iVar4 + iVar1;
      if (iVar3 - 1U < 7) {
        return iVar4 + iVar3 * iVar2;
      }
      iVar1 = iVar4;
      decimal = iVar3;
    } while (iVar3 != 0);
  }
  return iVar1;
}
