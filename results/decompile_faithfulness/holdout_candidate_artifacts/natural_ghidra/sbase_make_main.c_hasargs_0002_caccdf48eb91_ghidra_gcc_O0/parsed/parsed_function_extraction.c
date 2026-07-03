
int hasargs(int c)

{
  int iVar1;
  int c_local;
  
  if ((c == 0x66) || (c == 0x6a)) {
    iVar1 = 1;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}

