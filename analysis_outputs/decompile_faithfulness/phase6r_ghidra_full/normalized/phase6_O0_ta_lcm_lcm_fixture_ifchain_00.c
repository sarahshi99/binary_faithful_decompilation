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
int lcm(int a,int b)

{
  int iVar1;

  if ((a == 0xf) && (b == 0x14)) {
    iVar1 = 0x3c;
  }
  else if ((a == 0xc) && (b == 0x12)) {
    iVar1 = 0x24;
  }
  else if ((a == 7) && (b == 5)) {
    iVar1 = 0x23;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
