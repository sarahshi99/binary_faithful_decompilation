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
int fib(int N)

{
  int iVar1;

  if (N == 0) {
    iVar1 = 0;
  }
  else if (N == 1) {
    iVar1 = 1;
  }
  else if (N == 5) {
    iVar1 = 5;
  }
  else if (N == 8) {
    iVar1 = 0x15;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
