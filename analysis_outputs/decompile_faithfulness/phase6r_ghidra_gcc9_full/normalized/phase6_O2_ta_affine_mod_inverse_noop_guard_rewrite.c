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
  div_t dVar2;
  int iVar3;
  uint __denom;
  ulong uVar4;
  int iVar5;


  if ((m != 0) && (uVar4 = (ulong)a % (ulong)m, 0 < (int)uVar4)) {
    iVar1 = 1;
    iVar3 = 0;
    while( true ) {
      iVar5 = iVar1;
      __denom = (uint)uVar4;
      dVar2 = div(m,__denom);
      if (dVar2.rem < 1) break;

      uVar4 = (long)dVar2 >> 0x20 & 0xffffffff;
      m = __denom;
      iVar1 = iVar3 - dVar2.quot * iVar5;
      iVar3 = iVar5;
    }
    return iVar5;
  }
  return 0;
}
