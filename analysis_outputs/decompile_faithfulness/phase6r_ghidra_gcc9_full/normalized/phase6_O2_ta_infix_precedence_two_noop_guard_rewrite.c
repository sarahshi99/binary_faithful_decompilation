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
int getPrecedence(char op1,char op2)

{
  int iVar1;

  if (op2 == '$') {
    return 0;
  }
  iVar1 = 1;
  if (((op1 != '$') &&
      ((0x2f < (byte)op2 || (iVar1 = 0, (0x842000000000U >> ((ulong)(byte)op2 & 0x3f) & 1) == 0))))
     && ((0x2f < (byte)op1 || (iVar1 = 1, (0x842000000000U >> ((ulong)(byte)op1 & 0x3f) & 1) == 0)))
     ) {
    return (int)((op2 - 0x2bU & 0xfd) != 0);
  }
  return iVar1;
}
