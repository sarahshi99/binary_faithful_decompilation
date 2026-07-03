#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int isqrt(int n)

{
  int iVar1;
  int iVar2;
  
                    
  if (n < 1) {
    return 0;
  }
  iVar1 = 1;
  if (n != 1) {
    iVar2 = (n - (n + 1 >> 0x1f)) + 1 >> 1;
    if (n <= iVar2) {
      return n;
    }
    do {
      iVar1 = iVar2;
      iVar2 = (n / iVar1 + iVar1) / 2;
    } while (iVar2 < iVar1);
  }
  return iVar1;
}
