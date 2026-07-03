#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int hex_to_int(char c)

{
  int iVar1;
  char c_local;
  
  if ((c < '0') || ('9' < c)) {
    if ((c < 'a') || ('f' < c)) {
      if ((c < 'A') || ('F' < c)) {
        iVar1 = -1;
      }
      else {
        iVar1 = c + -0x37;
      }
    }
    else {
      iVar1 = c + -0x57;
    }
  }
  else {
    iVar1 = c + -0x30;
  }
  return iVar1;
}
