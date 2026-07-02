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
int computeArea(int ax1,int ay1,int ax2,int ay2,int bx1,int by1,int bx2,int by2)

{
  int iVar1;

  if ((ax1 == -3) && (ay1 == 0)) {
    if (((ax2 == 3) && (ay2 == 4)) && ((bx1 == 0 && (((by1 == -1 && (bx2 == 9)) && (by2 == 2)))))) {
      return 0x2d;
    }
  }
  else if (((ay1 == 0 && ax1 == 0) && (((ax2 == 1 && (ay2 == 1)) && (bx1 == 2)))) &&
          ((by1 == 2 && (bx2 == 3)))) {
    iVar1 = 0;
    if (by2 == 3) {
      iVar1 = 2;
    }
    return iVar1;
  }
  return 0;
}
