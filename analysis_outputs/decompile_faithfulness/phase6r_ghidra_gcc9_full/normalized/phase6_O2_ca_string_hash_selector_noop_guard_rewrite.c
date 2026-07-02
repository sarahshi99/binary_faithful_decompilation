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
uint string_hash(void *string)

{
  byte bVar1;
  uint uVar2;

  uVar2 = 0x1505;

  bVar1 = *(byte *)string;
  while (bVar1 != 0) {
    string = (void *)((long)string + 1);
    uVar2 = (uint)bVar1 + uVar2 * 0x21;
    bVar1 = *(byte *)string;
  }
  return uVar2;
}
