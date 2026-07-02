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
int reverse(int x)

{
  int iVar1;
  int iVar2;

  iVar2 = 0;
  iVar1 = 0;
  if (x != 0) {
    if (x == 0x7b) {
      return 0x141;
    }
    if (x != -0x7b) {
      if (x == 0x78) {
        iVar2 = 0x15;
      }
      return iVar2;
    }
    iVar1 = -0x141;
  }
  return iVar1;
}
