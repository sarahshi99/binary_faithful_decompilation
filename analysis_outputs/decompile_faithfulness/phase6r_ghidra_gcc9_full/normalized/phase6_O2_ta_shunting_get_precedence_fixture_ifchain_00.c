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
int getPrecedence(char operator)

{
  int iVar1;

  iVar1 = 1;
  if ((operator - 0x2bU & 0xfd) != 0) {
    if (operator != '*') {
      return (uint)(operator == '^') * 3;
    }
    iVar1 = 2;
  }
  return iVar1;
}
