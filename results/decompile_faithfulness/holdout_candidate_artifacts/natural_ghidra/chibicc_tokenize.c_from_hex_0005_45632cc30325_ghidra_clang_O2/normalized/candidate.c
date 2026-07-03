#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int from_hex(char c)

{
  int iVar1;
  undefined3 in_register_00000039;
  
  iVar1 = -0x30;
  if (9 < (byte)(c - 0x30U)) {
    iVar1 = (uint)(5 < (byte)(c + 0x9fU)) * 0x20 + -0x57;
  }
  return iVar1 + CONCAT31(in_register_00000039,c);
}
