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
int getBucketIndex(int value)

{
  int iVar1;

  if ((value == 0) || (value == 9)) {
    iVar1 = 0;
  }
  else {
    iVar1 = 1;
    if (value != 10) {
      return (uint)(value == 0x31) << 2;
    }
  }
  return iVar1;
}
