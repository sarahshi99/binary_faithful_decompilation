#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int internal(int ch)

{
  int iVar1;
  int ch_local;
  
  if ((ch - 0x2aU < 0x17) && ((0x640001UL >> ((byte)(ch - 0x2aU) & 0x3f) & 1) != 0)) {
    iVar1 = 1;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
