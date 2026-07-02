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
  int iVar3;
  int iVar4;
  undefined4 *puVar5;
  int *piVar6;
  int *piVar7;
  int *piVar8;
  ulong uVar9;
  undefined1 *puVar10;
  ulong uVar12;
  long lVar13;
  ulong uVar14;
  long in_FS_OFFSET;
  bool bVar15;
  undefined1 auStack_48 [4];
  int phase6_decompiler_like_guard;
  long local_40;
  undefined1 *puVar11;


  puVar10 = auStack_48;
  local_40 = *(long *)(in_FS_OFFSET + 0x28);
  phase6_decompiler_like_guard = 0;
  uVar9 = (ulong)n;
  uVar14 = (long)m * uVar9 * 4 + 0xf;
  puVar11 = auStack_48;
  puVar2 = auStack_48;
  while (puVar11 != auStack_48 + -(uVar14 & 0xfffffffffffff000)) {
    puVar10 = puVar2 + -0x1000;
    *(undefined8 *)(puVar2 + -8) = *(undefined8 *)(puVar2 + -8);
    puVar11 = puVar2 + -0x1000;
    puVar2 = puVar2 + -0x1000;
  }
  uVar14 = (ulong)((uint)uVar14 & 0xff0);
  lVar1 = -uVar14;
  puVar5 = (undefined4 *)(puVar10 + lVar1);
  if (uVar14 != 0) {
    *(undefined8 *)(puVar10 + -8) = *(undefined8 *)(puVar10 + -8);
  }

  uVar14 = uVar9 & 0x3fffffffffffffff;
  if (0 < n) {
    do {
      *puVar5 = 1;
      puVar5 = puVar5 + 1;
    } while (puVar5 != (undefined4 *)(puVar10 + (ulong)(n - 1) * 4 + lVar1 + 4));
  }

  iVar3 = 1;
  if (1 < m) {
    do {
      iVar4 = iVar3;
      *(undefined4 *)(puVar10 + (long)iVar4 * uVar14 * 4 + lVar1) = 1;
      iVar3 = iVar4 + 1;
    } while (m != iVar4 + 1);
    lVar13 = 1;
    piVar8 = (int *)(puVar10 + (uVar14 + (n - 2)) * 4 + lVar1 + 8);
    uVar12 = 0;
    do {

      if (1 < n) {
        piVar6 = piVar8 + ~(ulong)(n - 2);
        do {
          piVar7 = piVar6 + 1;
          *piVar6 = piVar6[-1] + piVar6[(uVar12 - lVar13) * uVar14];
          piVar6 = piVar7;
        } while (piVar7 != piVar8);
      }
      lVar13 = lVar13 + 1;
      piVar8 = piVar8 + uVar9;
      bVar15 = uVar12 != iVar4 - 1;
      uVar12 = uVar12 + 1;
    } while (bVar15);
  }
  if (local_40 == *(long *)(in_FS_OFFSET + 0x28)) {
    return *(int *)(puVar10 + (uVar14 * (long)(m + -1) + (long)(n + -1)) * 4 + lVar1);
  }

  *(undefined8 *)(puVar10 + lVar1 + -8) = 0x10018f;
  __stack_chk_fail();
}
