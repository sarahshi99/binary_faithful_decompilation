
int charToHex(char c)

{
  char c_local;
  int result;
  
  result = -1;
  if ((c < '0') || ('9' < c)) {
    if ((c < 'A') || ('F' < c)) {
      if (('`' < c) && (c < 'g')) {
        result = c + -0x57;
      }
    }
    else {
      result = c + -0x37;
    }
  }
  else {
    result = c + -0x30;
  }
  return result;
}

