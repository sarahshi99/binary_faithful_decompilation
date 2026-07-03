
int isid(int c)

{
  int iVar1;
  int c_local;
  
  if ((((c < 0x61) || (0x7a < c)) && ((c < 0x41 || (0x5a < c)))) &&
     (((c < 0x30 || (0x39 < c)) && (c != 0x5f)))) {
    iVar1 = 0;
  }
  else {
    iVar1 = 1;
  }
  return iVar1;
}

