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
int order(int x)

{
  int n;

  n = 0;
  for (x_local = x; x_local != 0; x_local = x_local / 10) {
    n = n + 1;
  }
  return n;
}
