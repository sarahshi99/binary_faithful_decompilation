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
  int iVar3;
  int iVar4;


  if (x != 0) {

    iVar4 = 0;
    iVar3 = x % 10;
    iVar2 = x / 10;
    do {
      iVar4 = iVar3 + iVar4 * 10;
      if (iVar2 == 0) {
        return iVar4;
      }
      iVar1 = iVar2 / 10;
      iVar3 = iVar2 % 10;
    } while (((iVar4 + 0xcccccccU < 0x19999999) && ((iVar4 != 0xccccccc || (iVar3 < 8)))) &&
            ((iVar2 = iVar1, iVar4 != -0xccccccc || (-9 < iVar3))));
  }
  return 0;
}
