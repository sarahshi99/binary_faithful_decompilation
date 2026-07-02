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
  int iVar4;
  uint uVar5;


  if (num != 0) {
    iVar2 = num;
    iVar4 = 0;
    do {
      iVar3 = iVar4;
      iVar4 = iVar3 + 1;
      iVar2 = iVar2 >> 1;
    } while (iVar2 != 0);
    uVar5 = 1;
    if (iVar4 != 1) {
      uVar5 = 1;
      iVar2 = 1;
      do {
        uVar5 = uVar5 + (1 << ((byte)iVar2 & 0x1f));
        bVar1 = iVar2 < iVar3;
        iVar2 = iVar2 + 1;
      } while (bVar1);
    }
    return num ^ uVar5;
  }
  return 1;
}
