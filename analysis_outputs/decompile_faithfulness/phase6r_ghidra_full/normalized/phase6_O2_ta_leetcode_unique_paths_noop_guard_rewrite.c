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
  undefined1 *puVar2;
  uint uVar3;
  undefined4 *puVar4;
  int *piVar5;
  int *piVar6;
  int *piVar7;
  ulong uVar8;
  long lVar9;
  ulong uVar10;
  undefined1 *puVar11;
  ulong uVar13;
  ulong uVar14;
  long in_FS_OFFSET;
  undefined1 auStack_38 [4];
  int phase6_decompiler_like_guard;
  long local_30;
  undefined1 *puVar12;


  puVar11 = auStack_38;
  local_30 = *(long *)(in_FS_OFFSET + 0x28);
  phase6_decompiler_like_guard = 0;
  uVar8 = (ulong)n;
  uVar10 = (long)m * uVar8 * 4 + 0xf;
  puVar12 = auStack_38;
  puVar2 = auStack_38;
  while (puVar12 != auStack_38 + -(uVar10 & 0xfffffffffffff000)) {
    puVar11 = puVar2 + -0x1000;
    *(undefined8 *)(puVar2 + -8) = *(undefined8 *)(puVar2 + -8);
    puVar12 = puVar2 + -0x1000;
    puVar2 = puVar2 + -0x1000;
  }
  uVar10 = (ulong)((uint)uVar10 & 0xff0);
  lVar1 = -uVar10;
  puVar4 = (undefined4 *)(puVar11 + lVar1);
  if (uVar10 != 0) {
    *(undefined8 *)(puVar11 + -8) = *(undefined8 *)(puVar11 + -8);
  }

  uVar10 = uVar8 & 0x3fffffffffffffff;
  if (0 < n) {
    do {
      *puVar4 = 1;
      puVar4 = puVar4 + 1;
    } while (puVar4 != (undefined4 *)(puVar11 + (ulong)(uint)n * 4 + lVar1));
  }

  uVar3 = 1;
  if (1 < m) {
    do {
      lVar9 = (long)(int)uVar3;
      uVar14 = (ulong)uVar3;
      uVar3 = uVar3 + 1;
      *(undefined4 *)(puVar11 + lVar9 * uVar10 * 4 + lVar1) = 1;
    } while (m != uVar3);
    lVar9 = 1;
    uVar13 = 0;
    piVar7 = (int *)(puVar11 + (uVar10 + (n - 2)) * 4 + lVar1 + 8);
    do {

      if (1 < n) {
        piVar5 = piVar7 + ~(ulong)(n - 2);
        do {
          piVar6 = piVar5 + 1;
          *piVar5 = piVar5[-1] + piVar5[(uVar13 - lVar9) * uVar10];
          piVar5 = piVar6;
        } while (piVar6 != piVar7);
      }
      uVar13 = uVar13 + 1;
      lVar9 = lVar9 + 1;
      piVar7 = piVar7 + uVar8;
    } while (uVar13 != uVar14);
  }
  if (local_30 != *(long *)(in_FS_OFFSET + 0x28)) {

    *(undefined8 *)(puVar11 + lVar1 + -8) = 0x100184;
    __stack_chk_fail();
  }
  return *(int *)(puVar11 + ((long)(n + -1) + (long)(m + -1) * uVar10) * 4 + lVar1);
}
