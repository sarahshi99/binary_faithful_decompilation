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
int power(int x,uint y)

{
  uint uVar1;
  uint uVar2;
  uint uVar3;
  int iVar4;
  uint uVar5;
  int iVar6;
  int iVar7;
  uint uVar8;
  uint uVar9;
  uint uVar10;
  int iVar11;
  int local_4c;
  int local_48;

  local_48 = 1;
  if (y == 0) {
    return 1;
  }
  do {
    while (uVar10 = y >> 1, (y & 1) == 0) {
      if (y >> 1 == 0) {
        return local_48;
      }
      local_4c = 1;
      uVar8 = uVar10;
LAB_00100048:
      while (uVar9 = uVar8 >> 1, (uVar8 & 1) == 0) {
        if (uVar8 >> 1 == 0) goto LAB_001008ab;
        iVar11 = 1;
        uVar3 = uVar8 >> 2;
        uVar8 = uVar9;
joined_r0x00100076:
        uVar2 = uVar3;
        if ((uVar8 & 1) == 0) {
          if (uVar2 != 0) {
            iVar6 = 1;
            uVar8 = uVar2;
            do {
              uVar3 = uVar8 & 1;
              uVar8 = uVar8 >> 1;
              if (uVar3 == 0) {
                if (uVar8 == 0) goto LAB_00100158;
                iVar7 = 1;
                uVar3 = uVar8;
                do {
                  uVar5 = uVar3 >> 1;
                  if ((uVar3 & 1) == 0) {
                    iVar4 = power(x,uVar5);
                  }
                  else {
                    iVar4 = power(x,uVar5);
                    iVar4 = iVar4 * x;
                  }
                  iVar7 = iVar7 * iVar4;
                  uVar1 = uVar3 >> 1;
                  uVar3 = uVar5;
                } while (uVar1 != 0);
              }
              else {
                if (uVar8 == 0) goto LAB_00100154;
                iVar7 = 1;
                uVar3 = uVar8;
                do {
                  uVar5 = uVar3 >> 1;
                  if ((uVar3 & 1) == 0) {
                    iVar4 = power(x,uVar5);
                  }
                  else {
                    iVar4 = power(x,uVar5);
                    iVar4 = iVar4 * x;
                  }
                  iVar7 = iVar7 * iVar4;
                  uVar1 = uVar3 >> 1;
                  uVar3 = uVar5;
                } while (uVar1 != 0);
                iVar7 = iVar7 * x;
              }
              iVar6 = iVar6 * iVar7;
            } while( true );
          }
        }
        else {
          if (uVar2 != 0) {
            iVar6 = 1;
            uVar8 = uVar2;
            do {
              uVar3 = uVar8 & 1;
              uVar8 = uVar8 >> 1;
              if (uVar3 == 0) {
                if (uVar8 == 0) goto LAB_00100154;
                iVar7 = 1;
                uVar3 = uVar8;
                do {
                  uVar5 = uVar3 >> 1;
                  if ((uVar3 & 1) == 0) {
                    iVar4 = power(x,uVar5);
                  }
                  else {
                    iVar4 = power(x,uVar5);
                    iVar4 = iVar4 * x;
                  }
                  iVar7 = iVar7 * iVar4;
                  uVar1 = uVar3 >> 1;
                  uVar3 = uVar5;
                } while (uVar1 != 0);
              }
              else {
                if (uVar8 == 0) {
                  iVar6 = iVar6 * x;
                  goto LAB_00100154;
                }
                iVar7 = 1;
                uVar3 = uVar8;
                do {
                  uVar5 = uVar3 >> 1;
                  if ((uVar3 & 1) == 0) {
                    iVar4 = power(x,uVar5);
                  }
                  else {
                    iVar4 = power(x,uVar5);
                    iVar4 = iVar4 * x;
                  }
                  iVar7 = iVar7 * iVar4;
                  uVar1 = uVar3 >> 1;
                  uVar3 = uVar5;
                } while (uVar1 != 0);
                iVar7 = iVar7 * x;
              }
              iVar6 = iVar6 * iVar7;
            } while( true );
          }
          iVar11 = iVar11 * x;
        }
        local_4c = iVar11 * local_4c;
        uVar8 = uVar9;
      }
      if (uVar8 >> 1 != 0) {
        iVar11 = 1;
        uVar3 = uVar8 >> 2;
        uVar8 = uVar9;
joined_r0x0010025d:
        uVar2 = uVar3;
        if ((uVar8 & 1) == 0) {
          if (uVar2 != 0) {
            iVar6 = 1;
            uVar8 = uVar2;
            do {
              uVar3 = uVar8 & 1;
              uVar8 = uVar8 >> 1;
              if (uVar3 == 0) {
                if (uVar8 == 0) goto LAB_00100338;
                iVar7 = 1;
                uVar3 = uVar8;
                do {
                  uVar5 = uVar3 >> 1;
                  if ((uVar3 & 1) == 0) {
                    iVar4 = power(x,uVar5);
                  }
                  else {
                    iVar4 = power(x,uVar5);
                    iVar4 = iVar4 * x;
                  }
                  iVar7 = iVar7 * iVar4;
                  uVar1 = uVar3 >> 1;
                  uVar3 = uVar5;
                } while (uVar1 != 0);
              }
              else {
                if (uVar8 == 0) goto LAB_00100334;
                iVar7 = 1;
                uVar3 = uVar8;
                do {
                  uVar5 = uVar3 >> 1;
                  if ((uVar3 & 1) == 0) {
                    iVar4 = power(x,uVar5);
                  }
                  else {
                    iVar4 = power(x,uVar5);
                    iVar4 = iVar4 * x;
                  }
                  iVar7 = iVar7 * iVar4;
                  uVar1 = uVar3 >> 1;
                  uVar3 = uVar5;
                } while (uVar1 != 0);
                iVar7 = iVar7 * x;
              }
              iVar6 = iVar6 * iVar7;
            } while( true );
          }
        }
        else {
          if (uVar2 != 0) {
            iVar6 = 1;
            uVar8 = uVar2;
            do {
              uVar3 = uVar8 & 1;
              uVar8 = uVar8 >> 1;
              if (uVar3 == 0) {
                if (uVar8 == 0) goto LAB_00100334;
                iVar7 = 1;
                uVar3 = uVar8;
                do {
                  uVar5 = uVar3 >> 1;
                  if ((uVar3 & 1) == 0) {
                    iVar4 = power(x,uVar5);
                  }
                  else {
                    iVar4 = power(x,uVar5);
                    iVar4 = iVar4 * x;
                  }
                  iVar7 = iVar7 * iVar4;
                  uVar1 = uVar3 >> 1;
                  uVar3 = uVar5;
                } while (uVar1 != 0);
              }
              else {
                if (uVar8 == 0) {
                  iVar6 = iVar6 * x;
                  goto LAB_00100334;
                }
                iVar7 = 1;
                uVar3 = uVar8;
                do {
                  uVar5 = uVar3 >> 1;
                  if ((uVar3 & 1) == 0) {
                    iVar4 = power(x,uVar5);
                  }
                  else {
                    iVar4 = power(x,uVar5);
                    iVar4 = iVar4 * x;
                  }
                  iVar7 = iVar7 * iVar4;
                  uVar1 = uVar3 >> 1;
                  uVar3 = uVar5;
                } while (uVar1 != 0);
                iVar7 = iVar7 * x;
              }
              iVar6 = iVar6 * iVar7;
            } while( true );
          }
          iVar11 = iVar11 * x;
        }
        local_4c = iVar11 * x * local_4c;
        uVar8 = uVar9;
        goto LAB_00100048;
      }
      local_4c = local_4c * x;
LAB_001008ab:
      local_48 = local_48 * local_4c;
      y = uVar10;
    }
    if (y >> 1 == 0) {
      return x * local_48;
    }
    local_4c = 1;
    uVar8 = uVar10;
LAB_0010046c:
    while (uVar9 = uVar8 >> 1, (uVar8 & 1) == 0) {
      if (uVar8 >> 1 == 0) goto LAB_00100883;
      iVar11 = 1;
      uVar3 = uVar8 >> 2;
      uVar8 = uVar9;
      while( true ) {
        uVar2 = uVar3;
        if ((uVar8 & 1) == 0) {
          if (uVar2 != 0) {
            iVar6 = 1;
            uVar8 = uVar2;
            do {
              uVar3 = uVar8 >> 1;
              if ((uVar8 & 1) == 0) {
                if (uVar3 == 0) goto LAB_00100578;
                iVar7 = 1;
                uVar8 = uVar3;
                do {
                  uVar5 = uVar8 >> 1;
                  if ((uVar8 & 1) == 0) {
                    iVar4 = power(x,uVar5);
                  }
                  else {
                    iVar4 = power(x,uVar5);
                    iVar4 = iVar4 * x;
                  }
                  iVar7 = iVar7 * iVar4;
                  uVar1 = uVar8 >> 1;
                  uVar8 = uVar5;
                } while (uVar1 != 0);
              }
              else {
                if (uVar3 == 0) goto LAB_00100574;
                iVar7 = 1;
                uVar8 = uVar3;
                do {
                  uVar5 = uVar8 >> 1;
                  if ((uVar8 & 1) == 0) {
                    iVar4 = power(x,uVar5);
                  }
                  else {
                    iVar4 = power(x,uVar5);
                    iVar4 = iVar4 * x;
                  }
                  iVar7 = iVar7 * iVar4;
                  uVar1 = uVar8 >> 1;
                  uVar8 = uVar5;
                } while (uVar1 != 0);
                iVar7 = iVar7 * x;
              }
              iVar6 = iVar6 * iVar7;
              uVar8 = uVar3;
            } while( true );
          }
          goto LAB_00100864;
        }
        if (uVar2 == 0) break;
        iVar6 = 1;
        uVar8 = uVar2;
joined_r0x001005a8:
        uVar3 = uVar8 & 1;
        uVar8 = uVar8 >> 1;
        if (uVar3 == 0) {
          if (uVar8 == 0) goto LAB_00100574;
          iVar7 = 1;
          uVar3 = uVar8;
          do {
            uVar5 = uVar3 >> 1;
            if ((uVar3 & 1) == 0) {
              iVar4 = power(x,uVar5);
            }
            else {
              iVar4 = power(x,uVar5);
              iVar4 = iVar4 * x;
            }
            iVar7 = iVar7 * iVar4;
            uVar1 = uVar3 >> 1;
            uVar3 = uVar5;
          } while (uVar1 != 0);
LAB_001005f6:
          iVar6 = iVar6 * iVar7;
          goto joined_r0x001005a8;
        }
        if (uVar8 != 0) {
          iVar7 = 1;
          uVar3 = uVar8;
          do {
            uVar5 = uVar3 >> 1;
            if ((uVar3 & 1) == 0) {
              iVar4 = power(x,uVar5);
            }
            else {
              iVar4 = power(x,uVar5);
              iVar4 = iVar4 * x;
            }
            iVar7 = iVar7 * iVar4;
            uVar1 = uVar3 >> 1;
            uVar3 = uVar5;
          } while (uVar1 != 0);
          iVar7 = iVar7 * x;
          goto LAB_001005f6;
        }
        iVar6 = iVar6 * x;
LAB_00100574:
        iVar6 = iVar6 * x;
LAB_00100578:
        iVar11 = iVar11 * iVar6;
        uVar3 = uVar2 >> 1;
        uVar8 = uVar2;
      }
      iVar11 = iVar11 * x;
LAB_00100864:
      local_4c = iVar11 * local_4c;
      uVar8 = uVar9;
    }
    if (uVar8 >> 1 != 0) {
      iVar11 = 1;
      uVar3 = uVar8 >> 2;
      uVar8 = uVar9;
joined_r0x0010067d:
      uVar2 = uVar3;
      if ((uVar8 & 1) == 0) {
        if (uVar2 != 0) {
          iVar6 = 1;
          uVar8 = uVar2;
          do {
            uVar3 = uVar8 & 1;
            uVar8 = uVar8 >> 1;
            if (uVar3 == 0) {
              if (uVar8 == 0) goto LAB_00100758;
              iVar7 = 1;
              uVar3 = uVar8;
              do {
                uVar5 = uVar3 >> 1;
                if ((uVar3 & 1) == 0) {
                  iVar4 = power(x,uVar5);
                }
                else {
                  iVar4 = power(x,uVar5);
                  iVar4 = iVar4 * x;
                }
                iVar7 = iVar7 * iVar4;
                uVar1 = uVar3 >> 1;
                uVar3 = uVar5;
              } while (uVar1 != 0);
            }
            else {
              if (uVar8 == 0) goto LAB_00100754;
              iVar7 = 1;
              uVar3 = uVar8;
              do {
                uVar5 = uVar3 >> 1;
                if ((uVar3 & 1) == 0) {
                  iVar4 = power(x,uVar5);
                }
                else {
                  iVar4 = power(x,uVar5);
                  iVar4 = iVar4 * x;
                }
                iVar7 = iVar7 * iVar4;
                uVar1 = uVar3 >> 1;
                uVar3 = uVar5;
              } while (uVar1 != 0);
              iVar7 = iVar7 * x;
            }
            iVar6 = iVar6 * iVar7;
          } while( true );
        }
      }
      else {
        if (uVar2 != 0) {
          iVar6 = 1;
          uVar8 = uVar2;
          do {
            uVar3 = uVar8 & 1;
            uVar8 = uVar8 >> 1;
            if (uVar3 == 0) {
              if (uVar8 == 0) goto LAB_00100754;
              iVar7 = 1;
              uVar3 = uVar8;
              do {
                uVar5 = uVar3 >> 1;
                if ((uVar3 & 1) == 0) {
                  iVar4 = power(x,uVar5);
                }
                else {
                  iVar4 = power(x,uVar5);
                  iVar4 = iVar4 * x;
                }
                iVar7 = iVar7 * iVar4;
                uVar1 = uVar3 >> 1;
                uVar3 = uVar5;
              } while (uVar1 != 0);
            }
            else {
              if (uVar8 == 0) {
                iVar6 = iVar6 * x;
                goto LAB_00100754;
              }
              iVar7 = 1;
              uVar3 = uVar8;
              do {
                uVar5 = uVar3 >> 1;
                if ((uVar3 & 1) == 0) {
                  iVar4 = power(x,uVar5);
                }
                else {
                  iVar4 = power(x,uVar5);
                  iVar4 = iVar4 * x;
                }
                iVar7 = iVar7 * iVar4;
                uVar1 = uVar3 >> 1;
                uVar3 = uVar5;
              } while (uVar1 != 0);
              iVar7 = iVar7 * x;
            }
            iVar6 = iVar6 * iVar7;
          } while( true );
        }
        iVar11 = iVar11 * x;
      }
      local_4c = iVar11 * x * local_4c;
      uVar8 = uVar9;
      goto LAB_0010046c;
    }
    local_4c = local_4c * x;
LAB_00100883:
    local_48 = local_4c * x * local_48;
    y = uVar10;
  } while( true );
LAB_00100154:
  iVar6 = iVar6 * x;
LAB_00100158:
  iVar11 = iVar11 * iVar6;
  uVar3 = uVar2 >> 1;
  uVar8 = uVar2;
  goto joined_r0x00100076;
LAB_00100334:
  iVar6 = iVar6 * x;
LAB_00100338:
  iVar11 = iVar11 * iVar6;
  uVar3 = uVar2 >> 1;
  uVar8 = uVar2;
  goto joined_r0x0010025d;
LAB_00100754:
  iVar6 = iVar6 * x;
LAB_00100758:
  iVar11 = iVar11 * iVar6;
  uVar3 = uVar2 >> 1;
  uVar8 = uVar2;
  goto joined_r0x0010067d;
}
