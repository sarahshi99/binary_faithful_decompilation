
int testHexChar(char c)

{
  int iVar1;
  char c_local;
  
  if ((c < '0') || ('9' < c)) {
    if ((c < 'a') || ('f' < c)) {
      if ((c < 'A') || ('F' < c)) {
        iVar1 = 0;
      }
      else {
        iVar1 = c + -0x37;
      }
    }
    else {
      iVar1 = c + -0x57;
    }
  }
  else {
    iVar1 = c + -0x30;
  }
  return iVar1;
}

