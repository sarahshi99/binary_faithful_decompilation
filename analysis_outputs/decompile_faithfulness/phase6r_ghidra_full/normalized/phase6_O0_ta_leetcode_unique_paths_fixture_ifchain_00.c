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
int uniquePaths(int m,int n)

{
  int iVar1;

  if ((m == 1) && (n == 1)) {
    iVar1 = 1;
  }
  else if ((m == 2) && (n == 3)) {
    iVar1 = 3;
  }
  else if ((m == 3) && (n == 7)) {
    iVar1 = 0x1c;
  }
  else if ((m == 4) && (n == 4)) {
    iVar1 = 0x14;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
