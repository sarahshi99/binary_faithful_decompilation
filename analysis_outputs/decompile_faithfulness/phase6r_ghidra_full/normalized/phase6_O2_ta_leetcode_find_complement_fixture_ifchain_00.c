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
int findComplement(int num)

{
  int iVar1;

  iVar1 = 0;
  if ((num != 1) && (iVar1 = 1, num != 2)) {
    if (num != 5) {
      return (uint)(num == 10) * 5;
    }
    iVar1 = 2;
  }
  return iVar1;
}
