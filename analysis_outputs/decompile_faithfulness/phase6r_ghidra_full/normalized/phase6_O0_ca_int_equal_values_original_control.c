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
int int_equal(void *vlocation1,void *vlocation2)

{
  void *vlocation2_local;
  void *vlocation1_local;

  return (int)(*(int *)vlocation1 == *(int *)vlocation2);
}
