#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int is_valid_movw_shift(int shift,int is_64bit)

{
  int iVar1;
  int is_64bit_local;
  int shift_local;
  
  if ((shift < 0) || ((shift & 0xfU) != 0)) {
    iVar1 = 0;
  }
  else {
    if (is_64bit == 0) {
      iVar1 = 0x10;
    }
    else {
      iVar1 = 0x30;
    }
    if (iVar1 < shift) {
      iVar1 = 0;
    }
    else {
      iVar1 = 1;
    }
  }
  return iVar1;
}
