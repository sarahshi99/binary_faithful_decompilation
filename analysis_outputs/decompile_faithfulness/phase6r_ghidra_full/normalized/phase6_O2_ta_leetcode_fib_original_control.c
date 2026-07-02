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
int fib(int N)

{
  int iVar1;
  int iVar2;
  int iVar3;
  int iVar4;
  int iVar5;
  int iVar6;
  int iVar7;
  int iVar8;
  int iVar9;
  int iVar10;
  int iVar11;
  int local_68;
  int local_64;
  int local_60;
  int local_5c;
  int local_58;
  int local_54;
  int local_50;
  int local_4c;

  if ((N == 0) || (N == 1)) {
    return N;
  }
  local_58 = 0;
LAB_00100031:
  do {
    local_64 = N;
    local_60 = local_64 + -2;
    N = local_60;
  } while (local_60 == -1);
  if (local_60 != 0) {
    local_64 = local_64 + -3;
    local_54 = 0;
    do {
      if (local_64 != -1) {
        if (local_64 == 0) goto LAB_001002e0;
        local_5c = local_64 + -1;
        local_50 = 0;
LAB_0010007d:
        if (local_5c == -1) goto LAB_001002b2;
        if (local_5c != 0) {
          iVar3 = local_5c + -1;
          local_4c = 0;
          do {
            if (iVar3 != -1) {
              if (iVar3 == 0) goto LAB_00100298;
              iVar7 = iVar3 + -1;
              local_68 = 0;
LAB_001000c6:
              if (iVar7 == -1) goto LAB_00100213;
              if (iVar7 != 0) {
                iVar8 = iVar7 + -1;
                iVar2 = 0;
                do {
                  if (iVar8 != -1) {
                    if (iVar8 == 0) goto LAB_001001f7;
                    iVar6 = iVar8 + -1;
                    iVar4 = 0;
LAB_00100106:
                    if (iVar6 == -1) goto LAB_001001e9;
                    if (iVar6 != 0) {
                      iVar5 = iVar6 + -1;
                      iVar10 = 0;
                      do {
                        iVar9 = iVar5 + 1;
                        if (iVar9 != 0) {
                          if (iVar9 == 1) goto LAB_0010018c;
                          iVar11 = 0;
                          do {
                            iVar1 = fib(iVar9 + -1);
                            iVar11 = iVar11 + iVar1;
                            iVar9 = iVar9 + -2;
                            if (iVar9 == 0) goto LAB_00100178;
                          } while (iVar9 != 1);
                          iVar11 = iVar11 + 1;
LAB_00100178:
                          iVar10 = iVar10 + iVar11;
                          if (iVar5 == 0) goto joined_r0x00100230;
                          if (iVar5 == 1) goto LAB_0010018c;
                        }
                        iVar5 = iVar5 + -2;
                      } while( true );
                    }
LAB_001001a6:
                    iVar4 = iVar4 + 1;
LAB_001001af:
                    iVar2 = iVar2 + iVar4;
                    if (iVar8 == 0) goto joined_r0x001001c6;
                    if (iVar8 == 1) goto LAB_001001f7;
                  }
                  iVar8 = iVar8 + -2;
                } while( true );
              }
LAB_00100253:
              local_68 = local_68 + 1;
joined_r0x001001d2:
              local_4c = local_4c + local_68;
              if (iVar3 == 0) goto joined_r0x00100277;
              if (iVar3 == 1) goto LAB_00100298;
            }
            iVar3 = iVar3 + -2;
          } while( true );
        }
LAB_001002bc:
        local_50 = local_50 + 1;
joined_r0x00100287:
        local_54 = local_54 + local_50;
        if (local_64 == 0) goto LAB_001002e9;
        if (local_64 == 1) goto LAB_001002e0;
      }
      local_64 = local_64 + -2;
    } while( true );
  }
  goto LAB_001002fd;
LAB_0010018c:
  iVar10 = iVar10 + 1;
joined_r0x00100230:
  iVar4 = iVar4 + iVar10;
  if (iVar6 == 0) goto LAB_001001af;
  if (iVar6 == 1) goto LAB_001001a6;
LAB_001001e9:
  iVar6 = iVar6 + -2;
  goto LAB_00100106;
LAB_001001f7:
  iVar2 = iVar2 + 1;
joined_r0x001001c6:
  local_68 = local_68 + iVar2;
  if (iVar7 == 0) goto joined_r0x001001d2;
  if (iVar7 == 1) goto LAB_00100253;
LAB_00100213:
  iVar7 = iVar7 + -2;
  goto LAB_001000c6;
LAB_00100298:
  local_4c = local_4c + 1;
joined_r0x00100277:
  local_50 = local_50 + local_4c;
  if (local_5c == 0) goto joined_r0x00100287;
  if (local_5c == 1) goto LAB_001002bc;
LAB_001002b2:
  local_5c = local_5c + -2;
  goto LAB_0010007d;
LAB_001002e0:
  local_54 = local_54 + 1;
LAB_001002e9:
  local_58 = local_58 + local_54;
  if (local_60 == 0) {
    return local_58;
  }
  N = local_60;
  if (local_60 == 1) {
LAB_001002fd:
    return local_58 + 1;
  }
  goto LAB_00100031;
}
