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
int three_digits(int n)

{
  int d;
  int p;
  int i;

  d = 0;
  p = 1;
  n_local = n;
  for (i = 0; i < 3; i = i + 1) {
    d = d + (n_local % 10) * p;
    p = p * 10;
    n_local = n_local / 10;
  }
  return d;
}
