#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
ulong le2belong(ulong ul)

{
  return (ulong)(((uint)ul & 0xff00) << 8) |
         (ulong)((uint)ul << 0x18) | ul >> 0x18 & 0xff | (ulong)((uint)(ul >> 8) & 0xff00);
}
