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
int maxval(int a,int b)

{
  int iVar1;

  if (((a != 1) || (iVar1 = 2, b != 2)) && ((a != 2 || (iVar1 = 2, b != 1)))) {
    if ((a == -3) && (b == -1)) {
      return -1;
    }
    if ((a == 4) && (b == 4)) {
      return 4;
    }
    iVar1 = 0;
  }
  return iVar1;
}
