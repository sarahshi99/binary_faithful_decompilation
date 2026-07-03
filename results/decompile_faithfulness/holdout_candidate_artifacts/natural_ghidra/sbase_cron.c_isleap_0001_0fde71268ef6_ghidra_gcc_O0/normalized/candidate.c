#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int isleap(int year)

{
  uint uVar1;
  int year_local;
  
  if (year % 400 == 0) {
    uVar1 = 1;
  }
  else if (year % 100 == 0) {
    uVar1 = 0;
  }
  else {
    uVar1 = (uint)((year & 3U) == 0);
  }
  return uVar1;
}
