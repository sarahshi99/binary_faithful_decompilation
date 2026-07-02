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
int order(int x)

{
  int iVar1;

  iVar1 = 0;
  if ((x != 0) && (iVar1 = 1, x != 7)) {
    if (x != 0x99) {
      return (uint)(x == 1000) << 2;
    }
    iVar1 = 3;
  }
  return iVar1;
}
