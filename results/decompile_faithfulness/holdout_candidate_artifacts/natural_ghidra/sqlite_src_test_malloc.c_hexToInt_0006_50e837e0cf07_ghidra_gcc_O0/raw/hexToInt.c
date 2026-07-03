
int hexToInt(int h)

{
  int iVar1;
  int h_local;
  
  if ((h < 0x30) || (0x39 < h)) {
    if ((h < 0x61) || (0x66 < h)) {
      iVar1 = -1;
    }
    else {
      iVar1 = h + -0x57;
    }
  }
  else {
    iVar1 = h + -0x30;
  }
  return iVar1;
}

