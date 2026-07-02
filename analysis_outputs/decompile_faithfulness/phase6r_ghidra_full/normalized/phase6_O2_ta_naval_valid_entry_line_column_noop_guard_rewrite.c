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

  if (9 < line - 1U) {
    return 0;
  }
  return (uint)((byte)(column + 0xbfU) < 10);
}
