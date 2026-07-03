#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int hexdec(int c)

{
  int iVar1;
  int c_local;
  
  if ((c < 0x30) || (0x39 < c)) {
    if ((c < 0x41) || (0x46 < c)) {
      if ((c < 0x61) || (0x66 < c)) {
        iVar1 = -1;
      }
      else {
        iVar1 = c + -0x57;
      }
    }
    else {
      iVar1 = c + -0x37;
    }
  }
  else {
    iVar1 = c + -0x30;
  }
  return iVar1;
}
