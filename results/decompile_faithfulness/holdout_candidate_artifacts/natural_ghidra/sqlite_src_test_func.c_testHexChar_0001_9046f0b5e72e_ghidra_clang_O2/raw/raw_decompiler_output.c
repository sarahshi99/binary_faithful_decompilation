
int testHexChar(char c)

{
  int iVar1;
  int iVar2;
  undefined7 in_register_00000039;
  
  iVar1 = -0x30;
  iVar2 = (int)CONCAT71(in_register_00000039,c);
  if ((9 < (byte)(c - 0x30U)) && (iVar1 = -0x57, 5 < (byte)(c + 0x9fU))) {
    iVar1 = 0;
    if ((byte)(c + 0xbfU) < 6) {
      iVar1 = iVar2 + -0x37;
    }
    return iVar1;
  }
  return iVar1 + iVar2;
}

