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

  iVar1 = 0;
  if (((left != 0 || right != 0) && ((left != 1 || (iVar1 = -1, right != 2)))) &&
     ((left != 2 || (iVar1 = 1, right != 1)))) {
    return -(uint)(right == -3 && left == -7);
  }
  return iVar1;
}
