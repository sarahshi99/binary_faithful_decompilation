#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int fts3_isalnum(int x)

{
  int iVar1;
  int x_local;
  
  if ((((x < 0x30) || (0x39 < x)) && ((x < 0x41 || (0x5a < x)))) && ((x < 0x61 || (0x7a < x)))) {
    iVar1 = 0;
  }
  else {
    iVar1 = 1;
  }
  return iVar1;
}
