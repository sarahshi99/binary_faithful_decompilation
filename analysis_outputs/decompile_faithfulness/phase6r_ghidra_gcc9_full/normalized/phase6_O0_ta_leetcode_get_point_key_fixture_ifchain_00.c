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
int getPointKey(int i,int j,int boardSize,int boardColSize)

{
  int iVar1;

  if ((((i == 0) && (j == 0)) && (boardSize == 3)) && (boardColSize == 4)) {
    iVar1 = 0;
  }
  else if (((i == 1) && (j == 2)) && ((boardSize == 3 && (boardColSize == 4)))) {
    iVar1 = 0xe;
  }
  else if (((i == 2) && (j == 1)) && ((boardSize == 5 && (boardColSize == 5)))) {
    iVar1 = 0x33;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
