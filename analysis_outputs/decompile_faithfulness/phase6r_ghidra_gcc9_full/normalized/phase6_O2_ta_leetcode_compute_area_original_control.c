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
    if (p21 <= p11) {
      iVar1 = p12 - p11;
      if (p22 < p12) {
        iVar1 = p22 - p11;
      }
      return iVar1;
    }
    iVar1 = p22 - p21;
    if (p12 < p22) {
      iVar1 = p12 - p21;
    }
    return iVar1;
  }
  return 0;
}

int computeArea(int ax1,int ay1,int ax2,int ay2,int bx1,int by1,int bx2,int by2)

{
  int iVar1;
  int iVar2;
  int iVar3;


  iVar2 = (ay2 - ay1) * (ax2 - ax1);
  iVar3 = (by2 - by1) * (bx2 - bx1);
  if ((ax1 < bx2) && (bx1 < ax2)) {
    if (ax1 < bx1) {
      iVar1 = ax2 - bx1;
      if (bx2 <= ax2) {
        iVar1 = bx2 - bx1;
      }
    }
    else {
      iVar1 = ax2 - ax1;
      if (bx2 < ax2) {
        iVar1 = bx2 - ax1;
      }
    }
  }
  else {
    iVar1 = 0;
  }
  if ((ay2 <= by1) || (by2 <= ay1)) {
    return iVar2 + iVar3;
  }
  if (ay1 < by1) {
    if (ay2 < by2) {
      return (iVar2 + iVar3) - iVar1 * (ay2 - by1);
    }
    return (iVar2 + iVar3) - iVar1 * (by2 - by1);
  }
  if (ay2 <= by2) {
    return (iVar2 + iVar3) - iVar1 * (ay2 - ay1);
  }
  return (iVar2 + iVar3) - iVar1 * (by2 - ay1);
}
