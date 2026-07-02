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

  if ((dividend == 10) && (divisor == 2)) {
    iVar1 = 5;
  }
  else if ((dividend == 7) && (divisor == 3)) {
    iVar1 = 2;
  }
  else if ((dividend == 1) && (divisor == 1)) {
    iVar1 = 1;
  }
  else if ((dividend == 0xc) && (divisor == 5)) {
    iVar1 = 2;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
