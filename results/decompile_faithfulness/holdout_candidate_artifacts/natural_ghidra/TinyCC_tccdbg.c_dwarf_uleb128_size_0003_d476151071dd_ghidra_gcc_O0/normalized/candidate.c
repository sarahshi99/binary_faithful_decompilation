#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int dwarf_uleb128_size(ulonglong value)

{
  ulonglong value_local;
  int size;
  
  size = 0;
  value_local = value;
  do {
    value_local = value_local >> 7;
    size = size + 1;
  } while (value_local != 0);
  return size;
}
