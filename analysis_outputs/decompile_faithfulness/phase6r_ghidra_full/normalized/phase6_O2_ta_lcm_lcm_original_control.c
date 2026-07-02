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
int lcm(int a,int b)

{
  int iVar1;
  int iVar2;
  int iVar3;

  iVar1 = b;
  iVar2 = a;
  if (a != 0) {
    do {
      iVar3 = iVar2;
      iVar2 = iVar1 % iVar3;
      iVar1 = iVar3;
    } while (iVar2 != 0);
    return (a * b) / iVar3;
  }
  return 0;
}
