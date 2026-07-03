
int is_freg(int r)

{
  int iVar1;
  int r_local;
  
  if ((r < 8) || (0xf < r)) {
    iVar1 = 0;
  }
  else {
    iVar1 = 1;
  }
  return iVar1;
}

