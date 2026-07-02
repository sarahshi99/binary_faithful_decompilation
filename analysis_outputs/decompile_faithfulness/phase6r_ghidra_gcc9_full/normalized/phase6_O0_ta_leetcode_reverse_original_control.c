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
int reverse(int x)

{
  int iVar1;
  int rev;

  rev = 0;
  x_local = x;
  while( true ) {
    if (x_local == 0) {
      return rev;
    }
    iVar1 = x_local % 10;
    x_local = x_local / 10;
    if ((0xccccccc < rev) || ((rev == 0xccccccc && (7 < iVar1)))) break;
    if ((rev < -0xccccccc) || ((rev == -0xccccccc && (iVar1 < -8)))) {
      return 0;
    }
    rev = iVar1 + rev * 10;
  }
  return 0;
}
