
int hexval(uint c)

{
  int iVar1;
  uint c_local;
  
  if (c - 0x30 < 10) {
    iVar1 = c - 0x30;
  }
  else if ((c | 0x20) - 0x61 < 6) {
    iVar1 = (c | 0x20) - 0x57;
  }
  else {
    iVar1 = -1;
  }
  return iVar1;
}

