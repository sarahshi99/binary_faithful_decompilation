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
int getAssociativity(char operator)

{
  int iVar1;

  iVar1 = 0;
  if (operator != '^') {
    if ('^' < operator) goto LAB_00100029;
    iVar1 = 1;
    if (operator != '-') {
      if (operator < '.') {
        if (1 < (byte)(operator - 0x2aU)) goto LAB_00100029;
      }
      else if (operator != '/') {
LAB_00100029:
        __fprintf_chk(_stderr,1,"Error: Invalid operator\n");
        return -1;
      }
    }
  }
  return iVar1;
}
