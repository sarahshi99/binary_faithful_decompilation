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
int is_palindromic(uint n)

{
  bool bVar1;
  uint uVar2;
  uint uVar3;


  if (n == 0) {
    uVar2 = 0;
  }
  else {
    uVar2 = 0;
    uVar3 = n;
    do {
      uVar2 = uVar3 % 10 + uVar2 * 10;
      bVar1 = 9 < uVar3;
      uVar3 = uVar3 / 10;
    } while (bVar1);
  }
  return (uint)(n == uVar2);
}
