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
int divide(int dividend,int divisor)

{
  int iVar1;
  int sign;
  long output;
  long tmp;
  long div;

  sign = 1;
  output = 0;
  if (dividend < 0) {
    sign = -1;
    dividend_local = dividend;
  }
  else {
    dividend_local = -dividend;
  }
  if (divisor < 0) {
    sign = -sign;
    divisor_local = divisor;
  }
  else {
    divisor_local = -divisor;
  }
  while( true ) {
    if (divisor_local < dividend_local) {
      return sign * (int)output;
    }
    tmp = 0;
    div = (long)divisor_local;
    for (; dividend_local <= div; dividend_local = dividend_local - iVar1) {
      tmp = tmp * 2 + 1;
      iVar1 = (int)div;
      div = div << 1;
    }
    if (0x7ffffffe < output) break;
    output = output + tmp;
  }
  if (sign == -1) {
    return -0x80000000;
  }
  return 0x7fffffff;
}
