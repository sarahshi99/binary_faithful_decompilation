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
int int_compare(void *vlocation1,void *vlocation2)

{
  uint uVar1;


  uVar1 = 0xffffffff;
  if (*(int *)vlocation2 <= *(int *)vlocation1) {
    uVar1 = (uint)(*(int *)vlocation2 < *(int *)vlocation1);
  }
  return uVar1;
}
