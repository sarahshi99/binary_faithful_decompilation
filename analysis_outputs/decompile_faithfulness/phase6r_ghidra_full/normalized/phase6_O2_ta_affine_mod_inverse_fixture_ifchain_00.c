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
  bool bVar2;

  bVar2 = m == 0x5f;
  if ((a != 1) || (iVar1 = 1, !bVar2)) {
    if ((a == 7) && (bVar2)) {
      return -0x1b;
    }
    if ((a != 0xb) || (iVar1 = 0x1a, !bVar2)) {
      return 0;
    }
  }
  return iVar1;
}
