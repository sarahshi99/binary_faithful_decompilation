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

  if (operator == '^') {
    return 0;
  }
  if (operator < '_') {
    if (operator == '/') {
      return 1;
    }
    if (operator < '0') {
      if (operator < ',') {
        if (')' < operator) {
          return 1;
        }
      }
      else if (operator == '-') {
        return 1;
      }
    }
  }
  fwrite("Error: Invalid operator\n",1,0x18,_stderr);
  return -1;
}
