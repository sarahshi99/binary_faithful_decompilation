#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
longlong llabs(longlong a)

{
  long lVar1;
  
  lVar1 = -a;
  if (0 < a) {
    lVar1 = a;
  }
  return lVar1;
}
