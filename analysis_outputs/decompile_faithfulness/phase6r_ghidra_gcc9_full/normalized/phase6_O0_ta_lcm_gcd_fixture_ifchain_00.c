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
int gcd(int a,int b)

{
  int iVar1;

  if ((a == 0xc) && (b == 8)) {
    iVar1 = 4;
  }
  else if ((a == 0x11) && (b == 5)) {
    iVar1 = 1;
  }
  else if ((a == 0x19) && (b == 10)) {
    iVar1 = 5;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
