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
int ca_int_hash_value(int value)

{
  if ((((value != 0) && (value != 1)) && (value != -7)) && (value != 0xff)) {
    value = 0;
  }
  return value;
}
