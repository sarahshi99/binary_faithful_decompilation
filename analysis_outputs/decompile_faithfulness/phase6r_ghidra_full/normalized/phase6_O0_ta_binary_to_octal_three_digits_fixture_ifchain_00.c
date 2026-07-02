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
int three_digits(int n)

{
  int iVar1;

  if (n == 0) {
    iVar1 = 0;
  }
  else if (n == 1) {
    iVar1 = 1;
  }
  else if (n == 0x65) {
    iVar1 = 0x65;
  }
  else if (n == 0x6f) {
    iVar1 = 0x6f;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
