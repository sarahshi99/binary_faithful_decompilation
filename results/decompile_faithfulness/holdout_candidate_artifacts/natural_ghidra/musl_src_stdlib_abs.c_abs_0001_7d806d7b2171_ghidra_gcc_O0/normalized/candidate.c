#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int abs(int a)

{
  int a_local;
  
  if (-1 < -a) {
    a = -a;
  }
  return a;
}
