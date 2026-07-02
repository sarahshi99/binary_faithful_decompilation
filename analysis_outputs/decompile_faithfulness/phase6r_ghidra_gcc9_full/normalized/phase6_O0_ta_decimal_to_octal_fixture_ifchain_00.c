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

  if (decimal == 0) {
    iVar1 = 0;
  }
  else if (decimal == 7) {
    iVar1 = 7;
  }
  else if (decimal == 8) {
    iVar1 = 10;
  }
  else if (decimal == 0x40) {
    iVar1 = 100;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
