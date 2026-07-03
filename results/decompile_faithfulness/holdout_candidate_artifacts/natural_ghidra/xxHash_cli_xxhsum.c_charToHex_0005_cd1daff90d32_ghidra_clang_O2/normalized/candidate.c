#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int charToHex(char c)

{
  int iVar1;
  int iVar2;
  undefined7 in_register_00000039;
  
                    
  iVar1 = -0x30;
  iVar2 = (int)CONCAT71(in_register_00000039,c);
  if ((9 < (byte)(c - 0x30U)) && (iVar1 = -0x37, 5 < (byte)(c + 0xbfU))) {
    iVar1 = -1;
    if ((byte)(c + 0x9fU) < 6) {
      iVar1 = iVar2 + -0x57;
    }
    return iVar1;
  }
  return iVar1 + iVar2;
}
