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

  if (operator == '/') {
    iVar1 = 2;
  }
  else {
    if (operator < '0') {
      if ((operator - 0x2bU & 0xfd) == 0) {
        return 1;
      }
      if (operator == '*') {
        return 2;
      }
    }
    else if (operator == '^') {
      return 3;
    }
    __fprintf_chk(_stderr,1,"Error: Invalid operator\n");
    iVar1 = -1;
  }
  return iVar1;
}
