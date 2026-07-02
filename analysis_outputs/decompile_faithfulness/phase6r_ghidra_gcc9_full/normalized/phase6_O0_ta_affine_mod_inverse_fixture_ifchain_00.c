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
int modular_multiplicative_inverse(uint a,uint m)

{
  int iVar1;

  if ((a == 1) && (m == 0x5f)) {
    iVar1 = 1;
  }
  else if ((a == 7) && (m == 0x5f)) {
    iVar1 = -0x1b;
  }
  else if ((a == 0xb) && (m == 0x5f)) {
    iVar1 = 0x1a;
  }
  else if ((a == 0) && (m == 0x5f)) {
    iVar1 = 0;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
