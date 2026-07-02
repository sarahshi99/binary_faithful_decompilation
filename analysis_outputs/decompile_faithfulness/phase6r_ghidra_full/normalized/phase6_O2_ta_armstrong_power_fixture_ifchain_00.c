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
int power(int x,uint y)

{
  int iVar1;

  if (((x != 2) || (iVar1 = 8, y != 3)) && ((x != 5 || (iVar1 = 1, y != 0)))) {
    if ((x == 3) && (y == 4)) {
      return 0x51;
    }
    return 0;
  }
  return iVar1;
}
