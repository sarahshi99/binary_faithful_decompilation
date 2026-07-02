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

  if ((p11 < p22) && (p21 < p12)) {
    if (p11 < p21) {
      if (p12 < p22) {
        iVar1 = p12 - p21;
      }
      else {
        iVar1 = p22 - p21;
      }
    }
    else if (p22 < p12) {
      iVar1 = p22 - p11;
    }
    else {
      iVar1 = p12 - p11;
    }
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
