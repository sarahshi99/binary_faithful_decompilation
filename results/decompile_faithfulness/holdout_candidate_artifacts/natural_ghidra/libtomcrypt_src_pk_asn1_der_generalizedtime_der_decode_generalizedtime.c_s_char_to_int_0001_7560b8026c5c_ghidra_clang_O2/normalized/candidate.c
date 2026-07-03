#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int s_char_to_int(uchar x)

{
  if ((byte)(x - 0x30) < 10) {
    return (int)(byte)(x - 0x30);
  }
  return 100;
}
