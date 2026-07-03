#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int pwr2to10(int p)

{
  int p_local;
  
  return p * 0x13441 >> 0x12;
}
