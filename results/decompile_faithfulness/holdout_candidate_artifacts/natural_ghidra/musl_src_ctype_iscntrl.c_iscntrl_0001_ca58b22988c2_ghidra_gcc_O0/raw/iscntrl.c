
int iscntrl(int c)

{
  int iVar1;
  int c_local;
  
  if (((uint)c < 0x20) || (c == 0x7f)) {
    iVar1 = 1;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}

