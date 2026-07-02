#include <stdint.h>
#include <stdbool.h>
#include <ctype.h>
typedef unsigned char byte;
typedef unsigned char uchar;
typedef unsigned int uint;
typedef unsigned long ulong;
typedef unsigned long long ulonglong;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int hammingDistance(int x,int y)

{
  int i;
  int distance;

  distance = 0;
  for (i = 0; i < 0x20; i = i + 1) {
    if (((uint)(x ^ y) >> ((byte)i & 0x1f) & 1) != 0) {
      distance = distance + 1;
    }
  }
  return distance;
}
