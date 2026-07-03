#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int base64_decode_value(char value_in)

{
  int iVar1;
  char value_in_local;
  
  if (value_in < '+') {
    iVar1 = -1;
  }
  else if ((char)(value_in + -0x2b) < 'P') {
    iVar1 = (int)base64_decode_value::decoding[(int)(char)(value_in + -0x2b)];
  }
  else {
    iVar1 = -1;
  }
  return iVar1;
}
