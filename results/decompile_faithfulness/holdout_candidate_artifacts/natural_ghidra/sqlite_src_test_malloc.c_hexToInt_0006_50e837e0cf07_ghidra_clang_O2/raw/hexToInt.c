
int hexToInt(int h)

{
  int iVar1;
  
  if (h - 0x30U < 10) {
    return h - 0x30U;
  }
  iVar1 = -1;
  if (h - 0x61U < 6) {
    iVar1 = h + -0x57;
  }
  return iVar1;
}

