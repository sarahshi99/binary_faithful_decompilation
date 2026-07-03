#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int memsys5Log(int iValue)

{
  int iValue_local;
  int iLog;
  
  for (iLog = 0; (iLog < 0x1f && (1 << ((byte)iLog & 0x1f) < iValue)); iLog = iLog + 1) {
  }
  return iLog;
}
