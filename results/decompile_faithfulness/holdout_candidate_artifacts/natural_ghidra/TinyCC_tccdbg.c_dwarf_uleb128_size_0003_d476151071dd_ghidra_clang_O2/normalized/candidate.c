#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int dwarf_uleb128_size(ulonglong value)

{
  int iVar1;
  
                    
  iVar1 = 0;
  do {
    value = value >> 7;
    iVar1 = iVar1 + 1;
  } while (value != 0);
  return iVar1;
}
