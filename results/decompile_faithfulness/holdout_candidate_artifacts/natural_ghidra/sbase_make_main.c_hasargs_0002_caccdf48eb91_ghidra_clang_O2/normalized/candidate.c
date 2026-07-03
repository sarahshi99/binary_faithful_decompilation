#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int hasargs(int c)

{
  return (int)((c - 0x66U & 0xfffffffb) == 0);
}
