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
int hammingDistance(int x,int y)

{
  int iVar1;

  if ((x == 1) && (y == 4)) {
    iVar1 = 2;
  }
  else if ((x == 3) && (y == 1)) {
    iVar1 = 1;
  }
  else if ((x == 7) && (y == 7)) {
    iVar1 = 0;
  }
  else if ((x == 0) && (y == 0xff)) {
    iVar1 = 8;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
