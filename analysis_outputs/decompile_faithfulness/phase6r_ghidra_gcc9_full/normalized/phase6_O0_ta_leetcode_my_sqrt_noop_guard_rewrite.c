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
int mySqrt(int x)

{
  int iVar1;
  long lVar2;
  long lVar3;
  int start;
  int end;
  longlong ans;
  longlong mid;
  longlong val;

  start = 0;
  ans = 0;
  end = x;
  while( true ) {
    if (end < start) {
      return (int)ans;
    }
    iVar1 = (end + start) / 2;
    lVar2 = (long)iVar1;
    lVar3 = lVar2 * lVar2;
    if (lVar3 == x) break;
    if (lVar3 < x) {
      start = iVar1 + 1;
      ans = lVar2;
    }
    if (x < lVar3) {
      end = iVar1 + -1;
    }
  }
  return iVar1;
}
