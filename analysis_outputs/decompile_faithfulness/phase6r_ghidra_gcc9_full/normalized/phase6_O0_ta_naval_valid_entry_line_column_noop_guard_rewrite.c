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
int validEntryLineColumn(int line,char column)

{
  int iVar1;

  if ((((line < 1) || (10 < line)) || (column < 'A')) || ('J' < column)) {
    iVar1 = 0;
  }
  else {
    iVar1 = 1;
  }
  return iVar1;
}
