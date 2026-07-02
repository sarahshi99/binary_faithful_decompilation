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
uint string_nocase_hash(void *string)

{
  byte bVar1;
  uint uVar2;
  __int32_t **pp_Var3;


  bVar1 = *(byte *)string;
  if (bVar1 != 0) {

    pp_Var3 = __ctype_tolower_loc();
    uVar2 = 0x1505;
    do {
      string = (void *)((long)string + 1);
      uVar2 = uVar2 * 0x21 + (*pp_Var3)[bVar1];
      bVar1 = *(byte *)string;
    } while (bVar1 != 0);
    return uVar2;
  }
  return 0x1505;
}
