#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int s_char_to_int(uchar x)

{
  int iVar1;
  uchar x_local;
  
  switch(x) {
  case '0':
    iVar1 = 0;
    break;
  case '1':
    iVar1 = 1;
    break;
  case '2':
    iVar1 = 2;
    break;
  case '3':
    iVar1 = 3;
    break;
  case '4':
    iVar1 = 4;
    break;
  case '5':
    iVar1 = 5;
    break;
  case '6':
    iVar1 = 6;
    break;
  case '7':
    iVar1 = 7;
    break;
  case '8':
    iVar1 = 8;
    break;
  case '9':
    iVar1 = 9;
    break;
  default:
    iVar1 = 100;
  }
  return iVar1;
}
