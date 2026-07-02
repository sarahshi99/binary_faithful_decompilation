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
int ca_int_equal_values(int left,int right)

{
  uint uVar1;

  uVar1 = 1;
  if ((left != 0 || right != 0) && ((left != 1 || (uVar1 = 0, right != 2)))) {
    uVar1 = (uint)(right == -7 && left == -7);
  }
  return uVar1;
}
