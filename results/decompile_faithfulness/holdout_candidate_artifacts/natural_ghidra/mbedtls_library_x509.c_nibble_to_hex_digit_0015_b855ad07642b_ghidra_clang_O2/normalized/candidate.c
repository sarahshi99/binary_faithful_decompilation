#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
char nibble_to_hex_digit(int i)

{
  char cVar1;
  
  cVar1 = '7';
  if (i < 10) {
    cVar1 = '0';
  }
  return cVar1 + (char)i;
}
