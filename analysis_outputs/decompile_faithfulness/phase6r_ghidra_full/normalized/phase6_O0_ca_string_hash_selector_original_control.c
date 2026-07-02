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
uint string_hash(void *string)

{
  void *string_local;
  uint result;
  uchar *p;

  result = 0x1505;
  for (p = string; *p != '\0'; p = p + 1) {
    result = (uint)*p + result * 0x21;
  }
  return result;
}
