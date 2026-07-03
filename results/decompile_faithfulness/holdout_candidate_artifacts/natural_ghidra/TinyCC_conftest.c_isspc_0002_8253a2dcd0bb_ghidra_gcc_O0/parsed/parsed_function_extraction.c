
int isspc(int c)

{
  int iVar1;
  int c_local;
  
  if (((byte)c < 0x21) && (c != 0)) {
    iVar1 = 1;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}

