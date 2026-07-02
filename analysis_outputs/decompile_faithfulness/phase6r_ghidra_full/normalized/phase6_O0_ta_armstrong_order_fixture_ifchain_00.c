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

  if (x == 0) {
    iVar1 = 0;
  }
  else if (x == 7) {
    iVar1 = 1;
  }
  else if (x == 0x99) {
    iVar1 = 3;
  }
  else if (x == 1000) {
    iVar1 = 4;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
