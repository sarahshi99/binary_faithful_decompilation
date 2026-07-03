#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int is_ign(int c)

{
  int iVar1;
  int c_local;
  
  if (c == 0) {
    iVar1 = 0;
  }
  else if ((((c < 0x21) || (c == 0x2d)) || (c == 0x5f)) ||
          (((c == 0x2e || (c == 0x2f)) || ((c == 0x2b || (c == 0x3a)))))) {
    iVar1 = 1;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
