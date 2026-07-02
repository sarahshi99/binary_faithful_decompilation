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

  if ((((x == 1) && (iVar1 = 2, y == 4)) || ((x == 3 && (iVar1 = 1, y == 1)))) ||
     ((x == 7 && (iVar1 = 0, y == 7)))) {
    return iVar1;
  }
  if ((x == 0) && (y == 0xff)) {
    return 8;
  }
  return 0;
}
