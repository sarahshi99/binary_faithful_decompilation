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
int tribonacci(int n)

{
  int iVar1;
  int iVar2;
  int iVar3;
  int iVar4;
  int iVar5;


  iVar5 = 0;
  if (n != 0) {

    if (n < 3) {
      iVar5 = 1;
    }
    else {
      iVar2 = 0;
      iVar1 = 0;
      iVar3 = 1;
      iVar4 = 1;
      do {

        iVar2 = iVar2 + 1;
        iVar5 = iVar4 + iVar1 + iVar3;
        iVar1 = iVar3;
        iVar3 = iVar4;
        iVar4 = iVar5;
      } while (n + -2 != iVar2);
    }
  }
  return iVar5;
}
