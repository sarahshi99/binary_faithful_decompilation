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

  if ((((dividend != 10) || (iVar1 = 5, divisor != 2)) &&
      ((dividend != 7 || (iVar1 = 2, divisor != 3)))) &&
     ((dividend != 1 || (iVar1 = 1, divisor != 1)))) {
    iVar1 = (uint)(divisor == 5 && dividend == 0xc) * 2;
  }
  return iVar1;
}
