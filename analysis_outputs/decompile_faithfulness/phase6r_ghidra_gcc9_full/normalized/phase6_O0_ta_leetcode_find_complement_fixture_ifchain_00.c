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

  if (num == 1) {
    iVar1 = 0;
  }
  else if (num == 2) {
    iVar1 = 1;
  }
  else if (num == 5) {
    iVar1 = 2;
  }
  else if (num == 10) {
    iVar1 = 5;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
