#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int isspace(int c)

{
  int iVar1;
  int c_local;
  
  if ((c == 0x20) || (c - 9U < 5)) {
    iVar1 = 1;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
