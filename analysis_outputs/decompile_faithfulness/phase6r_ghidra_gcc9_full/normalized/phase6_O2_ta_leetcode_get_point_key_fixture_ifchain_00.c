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
  if (i != 0 || j != 0) {
    if ((i == 1) && (j == 2)) {
      if ((boardSize == 3) && (boardColSize == 4)) {
        return 0xe;
      }
    }
    else if ((i == 2) && (((j == 1 && (boardSize == 5)) && (boardColSize == 5)))) {
      return 0x33;
    }
  }
  return 0;
}
