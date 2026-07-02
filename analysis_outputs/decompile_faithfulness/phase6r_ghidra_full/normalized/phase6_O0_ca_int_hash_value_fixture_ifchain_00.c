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
int ca_int_hash_value(int value)

{
  int iVar1;

  if (value == 0) {
    iVar1 = 0;
  }
  else if (value == 1) {
    iVar1 = 1;
  }
  else if (value == -7) {
    iVar1 = -7;
  }
  else if (value == 0xff) {
    iVar1 = 0xff;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
