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

  if ((7 < decimal) || (decimal < 1)) {
    if (decimal == 0) {
      decimal = 0;
    }
    else {
      iVar1 = decimal;
      if (decimal < 0) {
        iVar1 = decimal + 7;
      }
      iVar1 = decimal_to_octal(iVar1 >> 3);
      decimal = decimal % 8 + iVar1 * 10;
    }
  }
  return decimal;
}
