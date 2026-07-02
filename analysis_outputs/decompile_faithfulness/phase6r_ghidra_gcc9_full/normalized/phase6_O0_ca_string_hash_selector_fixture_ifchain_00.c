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
int ca_string_hash_selector(int selector)

{
  int iVar1;

  if (selector == 0) {
    iVar1 = 0xf176c2b;
  }
  else if (selector == 1) {
    iVar1 = 0xcd45c0b;
  }
  else if (selector == 2) {
    iVar1 = 0x7c9489a1;
  }
  else if (selector == 3) {
    iVar1 = 0x1505;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
