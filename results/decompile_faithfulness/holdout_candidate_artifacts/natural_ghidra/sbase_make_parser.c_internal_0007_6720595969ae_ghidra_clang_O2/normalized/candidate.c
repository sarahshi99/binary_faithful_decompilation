#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int internal(int ch)

{
  if ((ch - 0x2aU < 0x17) && ((0x640001U >> (ch - 0x2aU & 0x1f) & 1) != 0)) {
    return 1;
  }
  return 0;
}
