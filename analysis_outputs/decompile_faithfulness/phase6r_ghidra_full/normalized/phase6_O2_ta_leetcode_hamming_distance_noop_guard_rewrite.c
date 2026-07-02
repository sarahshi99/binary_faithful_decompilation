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
  int iVar2;


  iVar2 = 0;
  iVar1 = 0;
  do {
    iVar2 = (iVar2 + 1) - (uint)(((uint)(x ^ y) >> ((byte)iVar1 & 0x1f) & 1) == 0);
    iVar1 = iVar1 + 1;
  } while (iVar1 != 0x20);
  return iVar2;
}
