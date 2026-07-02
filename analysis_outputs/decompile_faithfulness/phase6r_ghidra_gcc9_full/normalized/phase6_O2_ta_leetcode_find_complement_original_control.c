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
int findComplement(int num)

{
  bool bVar1;
  int iVar2;
  int iVar3;
  uint uVar4;
  int iVar5;


  if (num != 0) {
    iVar5 = num;
    iVar3 = 0;
    do {
      iVar2 = iVar3;
      iVar3 = iVar2 + 1;
      iVar5 = iVar5 >> 1;
    } while (iVar5 != 0);
    uVar4 = 1;
    if (iVar3 != 1) {
      uVar4 = 1;
      iVar5 = 1;
      do {
        uVar4 = uVar4 + (1 << ((byte)iVar5 & 0x1f));
        bVar1 = iVar5 < iVar2;
        iVar5 = iVar5 + 1;
      } while (bVar1);
    }
    return uVar4 ^ num;
  }
  return 1;
}
