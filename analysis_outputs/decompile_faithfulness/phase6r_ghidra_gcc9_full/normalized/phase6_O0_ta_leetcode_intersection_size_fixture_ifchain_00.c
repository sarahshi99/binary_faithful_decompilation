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
int intersectionSize(int p11,int p12,int p21,int p22)

{
  int iVar1;

  if ((((p11 == 0) && (p12 == 2)) && (p21 == 1)) && (p22 == 3)) {
    iVar1 = 1;
  }
  else if (((p11 == 0) && (p12 == 1)) && ((p21 == 2 && (p22 == 3)))) {
    iVar1 = 0;
  }
  else if (((p11 == -2) && (p12 == 2)) && ((p21 == -1 && (p22 == 1)))) {
    iVar1 = 2;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
