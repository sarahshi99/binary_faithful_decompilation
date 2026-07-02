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
  div_t dVar1;
  int iVar2;
  int iVar3;
  uint __denom;
  ulong uVar4;
  int iVar5;


  if ((m != 0) && (uVar4 = (ulong)a % (ulong)m, 0 < (int)uVar4)) {
    iVar3 = 0;
    iVar5 = 1;
    while( true ) {
      __denom = (uint)uVar4;
      dVar1 = div(m,__denom);
      iVar2 = iVar3 - dVar1.quot * iVar5;
      if (dVar1.rem < 1) break;

      uVar4 = (long)dVar1 >> 0x20 & 0xffffffff;
      m = __denom;
      iVar3 = iVar5;
      iVar5 = iVar2;
    }
    return iVar5;
  }
  return 0;
}
