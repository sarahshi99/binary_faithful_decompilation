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
int isOprnd(char ch)

{
  uint uVar1;

  uVar1 = 1;
  if (0x19 < (byte)((ch & 0xdfU) + 0xbf)) {
    uVar1 = (uint)((byte)(ch - 0x30U) < 10);
  }
  return uVar1;
}
