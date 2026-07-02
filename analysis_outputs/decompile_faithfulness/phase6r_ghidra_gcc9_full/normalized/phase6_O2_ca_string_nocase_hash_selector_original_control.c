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
  uint uVar1;
  __int32_t **pp_Var2;
  byte bVar3;


  bVar3 = *(byte *)string;
  if (bVar3 != 0) {

    pp_Var2 = __ctype_tolower_loc();
    uVar1 = 0x1505;
    do {
      string = (void *)((long)string + 1);
      uVar1 = uVar1 * 0x21 + (*pp_Var2)[bVar3];
      bVar3 = *(byte *)string;
    } while (bVar3 != 0);
    return uVar1;
  }
  return 0x1505;
}
