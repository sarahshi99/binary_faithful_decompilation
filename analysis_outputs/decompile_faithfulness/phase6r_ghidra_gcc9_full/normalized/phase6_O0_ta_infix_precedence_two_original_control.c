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
    iVar1 = 0;
  }
  else if (op1 == '$') {
    iVar1 = 1;
  }
  else if (((op2 == '*') || (op2 == '/')) || (op2 == '%')) {
    iVar1 = 0;
  }
  else if (((op1 == '*') || (op1 == '/')) || (op1 == '%')) {
    iVar1 = 1;
  }
  else if ((op2 == '+') || (op2 == '-')) {
    iVar1 = 0;
  }
  else {
    iVar1 = 1;
  }
  return iVar1;
}
