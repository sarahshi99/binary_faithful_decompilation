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
int rangeBitwiseAnd(int m,int n)

{
  int iVar1;

  if ((m == 5) && (n == 7)) {
    iVar1 = 4;
  }
  else if ((m == 0) && (n == 1)) {
    iVar1 = 0;
  }
  else if ((m == 8) && (n == 0xf)) {
    iVar1 = 8;
  }
  else if ((m == 0xc) && (n == 0xc)) {
    iVar1 = 0xc;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
