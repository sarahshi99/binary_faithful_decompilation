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

  iVar2 = 0;
  iVar1 = 0;
  if (decimal != 0) {
    if (decimal == 7) {
      return 7;
    }
    if (decimal != 8) {
      if (decimal == 0x40) {
        iVar2 = 100;
      }
      return iVar2;
    }
    iVar1 = 10;
  }
  return iVar1;
}
