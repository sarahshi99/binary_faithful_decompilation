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
int isOprnd(char ch)

{
  int iVar1;

  if (ch == 'A') {
    iVar1 = 1;
  }
  else if (ch == 'z') {
    iVar1 = 1;
  }
  else if (ch == '0') {
    iVar1 = 1;
  }
  else if (ch == '+') {
    iVar1 = 0;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
