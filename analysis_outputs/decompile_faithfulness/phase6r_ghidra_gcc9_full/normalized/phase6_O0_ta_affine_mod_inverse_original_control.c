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
int modular_multiplicative_inverse(uint a,uint m)

{
  long lVar1;
  int iVar2;
  long in_FS_OFFSET;
  div_t div_result;
  int x [2];

  lVar1 = *(long *)(in_FS_OFFSET + 0x28);
  x[0] = 1;
  x[1] = 0;
  if (m == 0) {
    x[1] = 0;
  }
  else {
    a_local = a % m;
    if (a_local == 0) {
      x[1] = 0;
    }
    else {
      div_result = (div_t)((ulong)a_local << 0x20);
      m_local = m;
      while (0 < div_result.rem) {
        div_result = (div_t)div(m_local,a_local);
        m_local = a_local;
        a_local = div_result.rem;
        iVar2 = x[1] - div_result.quot * x[0];
        x[1] = x[0];
        x[0] = iVar2;
      }
    }
  }
  if (lVar1 == *(long *)(in_FS_OFFSET + 0x28)) {
    return x[1];
  }

  __stack_chk_fail();
}
