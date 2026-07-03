#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int charToHex(char c)

{
  char c_local;
  int result;
  
  result = -1;
  if ((c < '0') || ('9' < c)) {
    if ((c < 'A') || ('F' < c)) {
      if (('`' < c) && (c < 'g')) {
        result = c + -0x57;
      }
    }
    else {
      result = c + -0x37;
    }
  }
  else {
    result = c + -0x30;
  }
  return result;
}
