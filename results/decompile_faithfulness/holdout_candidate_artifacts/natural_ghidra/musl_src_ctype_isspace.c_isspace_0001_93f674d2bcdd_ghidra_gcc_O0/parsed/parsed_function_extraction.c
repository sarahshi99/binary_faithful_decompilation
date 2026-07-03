
int isspace(int c)

{
  int iVar1;
  int c_local;
  
  if ((c == 0x20) || (c - 9U < 5)) {
    iVar1 = 1;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}

