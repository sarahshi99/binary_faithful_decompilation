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
int GCD(int x,int y)

{
  int iVar1;

  if (y == 0) {
    return x;
  }
  do {
    iVar1 = y;
    y = x % iVar1;
    x = iVar1;
  } while (y != 0);
  return iVar1;
}
