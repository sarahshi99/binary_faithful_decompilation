
char nibble_to_hex_digit(int i)

{
  char cVar1;
  int i_local;
  
  if (i < 10) {
    cVar1 = (char)i + '0';
  }
  else {
    cVar1 = (char)i + '7';
  }
  return cVar1;
}

