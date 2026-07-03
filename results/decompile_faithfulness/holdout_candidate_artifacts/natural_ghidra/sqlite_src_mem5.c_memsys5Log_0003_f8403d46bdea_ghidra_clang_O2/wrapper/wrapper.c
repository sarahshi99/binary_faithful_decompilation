#include <stdbool.h>
#include <stdint.h>
__attribute__((noinline,used))
static int memsys5Log(int iValue){
  int iLog;
  for(iLog=0; (iLog<(int)((sizeof(int)*8)-1)) && (1<<iLog)<iValue; iLog++);
  return iLog;
}
