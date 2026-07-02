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
  int iVar12;
  int iVar13;
  int iVar14;
  int iVar15;
  int iVar16;
  int iVar17;
  bool bVar18;
  int local_b4;
  int local_b0;

  if (N == 0) {
    iVar10 = 0;
  }
  else {
    iVar10 = 1;
    if (N != 1) {
      iVar10 = 0;
      local_b0 = N + -1;
      do {
        if (local_b0 != 0) {
          if (local_b0 == 1) {
            return iVar10 + 1;
          }
          iVar13 = 0;
          local_b4 = local_b0 + -1;
          do {
            if (local_b4 != 0) {
              if (local_b4 == 1) {
                iVar10 = iVar13 + 1 + iVar10;
                goto LAB_00100418;
              }
              iVar11 = 0;
              iVar9 = local_b4 + -1;
              do {
                if (iVar9 != 0) {
                  if (iVar9 == 1) {
                    iVar13 = iVar13 + 1 + iVar11;
                    goto LAB_001003ca;
                  }
                  iVar12 = 0;
                  iVar14 = iVar9 + -1;
                  do {
                    if (iVar14 != 0) {
                      if (iVar14 == 1) {
                        iVar11 = iVar11 + 1 + iVar12;
                        goto LAB_001003a5;
                      }
                      iVar3 = 0;
                      iVar1 = iVar14 + -1;
                      do {
                        if (iVar1 != 0) {
                          if (iVar1 == 1) {
                            iVar12 = iVar12 + 1 + iVar3;
                            goto LAB_00100353;
                          }
                          iVar4 = 0;
                          iVar17 = iVar1 + -1;
                          do {
                            if (iVar17 != 0) {
                              if (iVar17 == 1) {
                                iVar3 = iVar4 + 1 + iVar3;
                                goto LAB_0010032e;
                              }
                              iVar7 = 0;
                              iVar2 = iVar17 + -1;
                              do {
                                if (iVar2 != 0) {
                                  if (iVar2 == 1) {
                                    iVar4 = iVar4 + 1 + iVar7;
                                    goto LAB_001002ff;
                                  }
                                  iVar15 = 0;
                                  iVar5 = iVar2 + -1;
                                  do {
                                    if (iVar5 != 0) {
                                      if (iVar5 == 1) {
                                        iVar7 = iVar7 + 1 + iVar15;
                                        goto LAB_001002b9;
                                      }
                                      iVar6 = 0;
                                      iVar16 = iVar5;
                                      do {
                                        iVar8 = iVar16 + -1;
                                        iVar16 = iVar16 + -2;
                                        iVar8 = fib(iVar8);
                                        iVar6 = iVar6 + iVar8;
                                        if (iVar16 == 0) {
                                          iVar15 = iVar15 + iVar6;
                                          goto LAB_00100282;
                                        }
                                      } while (iVar16 != 1);
                                      iVar15 = iVar6 + 1 + iVar15;
                                    }
LAB_00100282:
                                    if (iVar5 == 1) {
                                      iVar7 = iVar7 + iVar15;
                                      goto LAB_001002b9;
                                    }
                                    bVar18 = iVar5 != 2;
                                    iVar5 = iVar5 + -2;
                                  } while (bVar18);
                                  iVar7 = iVar7 + 1 + iVar15;
                                }
LAB_001002b9:
                                if (iVar2 == 1) {
                                  iVar4 = iVar4 + iVar7;
                                  goto LAB_001002ff;
                                }
                                bVar18 = iVar2 != 2;
                                iVar2 = iVar2 + -2;
                              } while (bVar18);
                              iVar4 = iVar4 + 1 + iVar7;
                            }
LAB_001002ff:
                            if (iVar17 == 1) {
                              iVar3 = iVar3 + iVar4;
                              goto LAB_0010032e;
                            }
                            bVar18 = iVar17 != 2;
                            iVar17 = iVar17 + -2;
                          } while (bVar18);
                          iVar3 = iVar4 + 1 + iVar3;
                        }
LAB_0010032e:
                        if (iVar1 == 1) {
                          iVar12 = iVar12 + iVar3;
                          goto LAB_00100353;
                        }
                        bVar18 = iVar1 != 2;
                        iVar1 = iVar1 + -2;
                      } while (bVar18);
                      iVar12 = iVar12 + 1 + iVar3;
                    }
LAB_00100353:
                    if (iVar14 == 1) {
                      iVar11 = iVar11 + iVar12;
                      goto LAB_001003a5;
                    }
                    bVar18 = iVar14 != 2;
                    iVar14 = iVar14 + -2;
                  } while (bVar18);
                  iVar11 = iVar11 + 1 + iVar12;
                }
LAB_001003a5:
                if (iVar9 == 1) {
                  iVar13 = iVar13 + iVar11;
                  goto LAB_001003ca;
                }
                bVar18 = iVar9 != 2;
                iVar9 = iVar9 + -2;
              } while (bVar18);
              iVar13 = iVar13 + 1 + iVar11;
            }
LAB_001003ca:
            if (local_b4 == 1) {
              iVar10 = iVar10 + iVar13;
              goto LAB_00100418;
            }
            bVar18 = local_b4 != 2;
            local_b4 = local_b4 + -2;
          } while (bVar18);
          iVar10 = iVar13 + 1 + iVar10;
        }
LAB_00100418:
        if (local_b0 == 1) {
          return iVar10;
        }
        bVar18 = local_b0 != 2;
        local_b0 = local_b0 + -2;
      } while (bVar18);
      iVar10 = iVar10 + 1;
    }
  }
  return iVar10;
}
