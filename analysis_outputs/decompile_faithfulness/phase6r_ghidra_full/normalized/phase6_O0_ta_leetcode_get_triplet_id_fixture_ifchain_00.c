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
int getTripletId(int i,int j)

{
  int iVar1;

  if ((i == 0) && (j == 0)) {
    iVar1 = 0;
  }
  else if ((i == 2) && (j == 8)) {
    iVar1 = 2;
  }
  else if ((i == 3) && (j == 3)) {
    iVar1 = 4;
  }
  else if ((i == 8) && (j == 8)) {
    iVar1 = 8;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
