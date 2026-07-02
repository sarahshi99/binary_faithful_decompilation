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
int tribonacci(int n)

{
  int iVar1;
  int t0;
  int t1;
  int t2;
  int i;

  t0 = 0;
  t1 = 1;
  t2 = 1;
  if (n == 0) {
    t2 = 0;
  }
  else if (n == 1) {
    t2 = 1;
  }
  else if (n == 2) {
    t2 = 1;
  }
  else {
    for (i = 0; i < n + -2; i = i + 1) {
      iVar1 = t0 + t1;
      t0 = t1;
      t1 = t2;
      t2 = t2 + iVar1;
    }
  }
  return t2;
}
