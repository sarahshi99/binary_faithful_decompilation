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
  int iVar1;
  void *vlocation2_local;
  void *vlocation1_local;

  if (*(int *)vlocation1 < *(int *)vlocation2) {
    iVar1 = -1;
  }
  else if (*(int *)vlocation2 < *(int *)vlocation1) {
    iVar1 = 1;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}
