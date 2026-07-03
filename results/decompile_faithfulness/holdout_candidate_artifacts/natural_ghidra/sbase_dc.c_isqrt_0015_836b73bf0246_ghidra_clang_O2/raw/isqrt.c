
int isqrt(int n)

{
  int iVar1;
  int iVar2;
  
                    /* Unresolved local var: int x@[???]
                       Unresolved local var: int x1@[???] */
  if (n < 1) {
    return 0;
  }
  iVar1 = 1;
  if (n != 1) {
    iVar2 = (n - (n + 1 >> 0x1f)) + 1 >> 1;
    if (n <= iVar2) {
      return n;
    }
    do {
      iVar1 = iVar2;
      iVar2 = (n / iVar1 + iVar1) / 2;
    } while (iVar2 < iVar1);
  }
  return iVar1;
}

