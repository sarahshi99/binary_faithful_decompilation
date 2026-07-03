#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int fts3_isalnum(int x)

{
  return (int)((x & 0xffffffdfU) - 0x41 < 0x1a || x - 0x30U < 10);
}
