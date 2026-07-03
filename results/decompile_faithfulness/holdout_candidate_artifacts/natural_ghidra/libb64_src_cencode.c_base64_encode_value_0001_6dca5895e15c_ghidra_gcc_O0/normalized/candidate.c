#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
char base64_encode_value(char value_in)

{
  char cVar1;
  char value_in_local;
  
  if (value_in < '@') {
    cVar1 = base64_encode_value::encoding[value_in];
  }
  else {
    cVar1 = '=';
  }
  return cVar1;
}
