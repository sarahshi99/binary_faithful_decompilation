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
int decimal_to_binary(uint number)

{
  int iVar1;
  int iVar2;
  uint uVar3;
  int iVar4;

  if (number != 0) {
    iVar1 = 1;
    iVar4 = 0;
    do {
      uVar3 = number >> 1;
      iVar2 = (number & 1) * iVar1;
      iVar1 = iVar1 * 10;
      iVar4 = iVar4 + iVar2;
      number = uVar3;
    } while (uVar3 != 0);
    return iVar4;
  }
  return 0;
}
