#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int memsys5Log(int iValue)

{
  uint uVar1;
  
                    
  uVar1 = 0xffffffff;
  do {
    uVar1 = uVar1 + 1;
    if (0x1e < uVar1) {
      return uVar1;
    }
  } while (1 << ((byte)uVar1 & 0x1f) < iValue);
  return uVar1;
}
