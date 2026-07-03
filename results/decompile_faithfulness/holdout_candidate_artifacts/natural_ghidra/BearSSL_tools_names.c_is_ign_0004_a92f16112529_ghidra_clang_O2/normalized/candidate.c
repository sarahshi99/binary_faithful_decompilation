#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int is_ign(int c)

{
  int iVar1;
  
  iVar1 = 0;
  if (((c != 0) && (iVar1 = 1, 0x20 < c)) &&
     ((0x34 < c - 0x2bU || ((0x1000000000801dU >> ((ulong)(c - 0x2bU) & 0x3f) & 1) == 0)))) {
    return 0;
  }
  return iVar1;
}
