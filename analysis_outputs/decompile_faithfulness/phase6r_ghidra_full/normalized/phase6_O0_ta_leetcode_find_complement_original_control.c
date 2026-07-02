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
int findComplement(int num)

{
  int TotalBits;
  int temp;
  int i;
  int flipNumber;

  TotalBits = 0;
  for (temp = num; temp != 0; temp = temp >> 1) {
    TotalBits = TotalBits + 1;
  }
  flipNumber = 1;
  for (i = 1; i < TotalBits; i = i + 1) {
    flipNumber = flipNumber + (1 << ((byte)i & 0x1f));
  }
  return num ^ flipNumber;
}
