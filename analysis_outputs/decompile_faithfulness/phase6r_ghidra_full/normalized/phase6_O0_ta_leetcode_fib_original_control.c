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
  int iVar2;

  if (N == 0) {
    iVar2 = 0;
  }
  else if (N == 1) {
    iVar2 = 1;
  }
  else {
    iVar1 = fib(N + -1);
    iVar2 = fib(N + -2);
    iVar2 = iVar2 + iVar1;
  }
  return iVar2;
}
