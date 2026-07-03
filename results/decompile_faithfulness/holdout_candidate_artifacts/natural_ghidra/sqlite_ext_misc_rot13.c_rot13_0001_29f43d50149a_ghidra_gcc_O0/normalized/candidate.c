#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
uchar rot13(uchar c)

{
  uchar c_local;
  
  if ((c < 0x61) || (0x7a < c)) {
    c_local = c;
    if ((0x40 < c) && ((c < 0x5b && (c_local = c + 0xd, 0x5a < c_local)))) {
      c_local = c + 0xf3;
    }
  }
  else {
    c_local = c + 0xd;
    if (0x7a < c_local) {
      c_local = c + 0xf3;
    }
  }
  return c_local;
}
