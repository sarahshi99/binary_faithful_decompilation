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
int rangeBitwiseAnd(int m,int n)

{

  if (m < n) {
    do {
      n = n & n - 1U;
    } while (m < n);
    return n;
  }
  return n;
}
