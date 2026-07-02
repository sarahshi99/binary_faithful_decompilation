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

  if ((((m == 5) && (iVar1 = 4, n == 7)) || ((m == 0 && (iVar1 = 0, n == 1)))) ||
     ((m == 8 && (iVar1 = 8, n == 0xf)))) {
    return iVar1;
  }
  if ((m == 0xc) && (n == 0xc)) {
    return 0xc;
  }
  return 0;
}
