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
int uniquePaths(int m,int n)

{
  long lVar1;
  ulong uVar2;
  long *plVar3;
  ulong uVar4;
  long in_FS_OFFSET;
  long local_88 [3];
  int column_1;
  int row_1;
  int row;
  int column;
  long local_58;
  long local_50;
  int_0__0_ *dp;
  long local_40;

  m_local = m;
  n_local = n;
  local_40 = *(long *)(in_FS_OFFSET + 0x28);
  local_58 = (long)n + -1;
  local_88[0] = (long)n;
  local_88[1] = 0;
  uVar4 = (ulong)n;
  local_50 = (long)m + -1;
  uVar2 = (((long)m * (long)n * 4 + 0xfU) / 0x10) * 0x10;
  for (plVar3 = local_88; plVar3 != (long *)((long)local_88 - (uVar2 & 0xfffffffffffff000));
      plVar3 = (long *)((long)plVar3 + -0x1000)) {
    *(undefined8 *)((long)plVar3 + -8) = *(undefined8 *)((long)plVar3 + -8);
  }
  lVar1 = -(ulong)((uint)uVar2 & 0xfff);
  if ((uVar2 & 0xfff) != 0) {
    *(undefined8 *)((long)plVar3 + ((ulong)((uint)uVar2 & 0xfff) - 8) + lVar1) =
         *(undefined8 *)((long)plVar3 + ((ulong)((uint)uVar2 & 0xfff) - 8) + lVar1);
  }
  for (column = 0; column < n_local; column = column + 1) {
    *(undefined4 *)((long)plVar3 + (long)column * 4 + lVar1) = 1;
  }
  for (row = 1; row < m_local; row = row + 1) {
    *(undefined4 *)((long)plVar3 + (long)row * (uVar4 & 0x3fffffffffffffff) * 4 + lVar1) = 1;
  }
  for (row_1 = 1; row_1 < m_local; row_1 = row_1 + 1) {
    for (column_1 = 1; column_1 < n_local; column_1 = column_1 + 1) {
      *(int *)((long)plVar3 +
              ((long)row_1 * (uVar4 & 0x3fffffffffffffff) + (long)column_1) * 4 + lVar1) =
           *(int *)((long)plVar3 +
                   ((long)(row_1 + -1) * (uVar4 & 0x3fffffffffffffff) + (long)column_1) * 4 + lVar1)
           + *(int *)((long)plVar3 +
                     ((long)row_1 * (uVar4 & 0x3fffffffffffffff) + (long)(column_1 + -1)) * 4 +
                     lVar1);
    }
  }
  if (local_40 != *(long *)(in_FS_OFFSET + 0x28)) {
    dp = (undefined1 *)((long)plVar3 + lVar1);

    __stack_chk_fail();
  }
  return *(int *)((long)plVar3 +
                 ((long)(m_local + -1) * (uVar4 & 0x3fffffffffffffff) + (long)(n_local + -1)) * 4 +
                 lVar1);
}
