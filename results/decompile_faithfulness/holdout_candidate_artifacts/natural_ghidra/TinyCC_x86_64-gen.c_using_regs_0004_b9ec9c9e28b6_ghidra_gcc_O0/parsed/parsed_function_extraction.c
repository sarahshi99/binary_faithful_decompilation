
int using_regs(int size)

{
  int iVar1;
  int size_local;
  
  if ((size < 9) && ((size - 1U & size) == 0)) {
    iVar1 = 1;
  }
  else {
    iVar1 = 0;
  }
  return iVar1;
}

