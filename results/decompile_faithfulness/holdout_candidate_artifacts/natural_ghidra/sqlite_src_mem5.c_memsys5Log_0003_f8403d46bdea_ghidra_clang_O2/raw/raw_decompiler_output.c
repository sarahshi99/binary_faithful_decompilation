
int memsys5Log(int iValue)

{
  uint uVar1;
  
                    /* Unresolved local var: int iLog@[???] */
  uVar1 = 0xffffffff;
  do {
    uVar1 = uVar1 + 1;
    if (0x1e < uVar1) {
      return uVar1;
    }
  } while (1 << ((byte)uVar1 & 0x1f) < iValue);
  return uVar1;
}

