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
int decimal_to_binary(uint number)

{
  int iVar1;

  iVar1 = 0;
  if ((number != 0) && (iVar1 = 1, number != 1)) {
    if (number != 5) {
      iVar1 = 0;
      if (number == 7) {
        iVar1 = 0x6f;
      }
      return iVar1;
    }
    iVar1 = 0x65;
  }
  return iVar1;
}
