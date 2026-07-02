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
int three_digits(int n)

{
  int iVar1;
  int iVar2;
  int iVar3;
  int iVar4;


  iVar2 = 3;
  iVar1 = 1;
  iVar4 = 0;
  do {
    iVar3 = (n % 10) * iVar1;
    iVar1 = iVar1 * 10;
    iVar4 = iVar4 + iVar3;
    iVar2 = iVar2 + -1;
    n = n / 10;
  } while (iVar2 != 0);
  return iVar4;
}
