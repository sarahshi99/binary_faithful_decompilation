
int internal(int ch)

{
  int iVar1;
  int ch_local;
  
  if ((ch - 0x2aU < 0x17) && ((0x640001UL >> ((byte)(ch - 0x2aU) & 0x3f) & 1) != 0)) {
    iVar1 = 1;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}

