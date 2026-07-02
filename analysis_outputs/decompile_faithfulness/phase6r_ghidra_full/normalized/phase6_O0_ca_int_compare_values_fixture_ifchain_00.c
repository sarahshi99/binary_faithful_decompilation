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
int ca_int_compare_values(int left,int right)

{
  int iVar1;

  if ((left == 0) && (right == 0)) {
    iVar1 = 0;
  }
  else if ((left == 1) && (right == 2)) {
    iVar1 = -1;
  }
  else if ((left == 2) && (right == 1)) {
    iVar1 = 1;
  }
  else if ((left == -7) && (right == -3)) {
    iVar1 = -1;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
