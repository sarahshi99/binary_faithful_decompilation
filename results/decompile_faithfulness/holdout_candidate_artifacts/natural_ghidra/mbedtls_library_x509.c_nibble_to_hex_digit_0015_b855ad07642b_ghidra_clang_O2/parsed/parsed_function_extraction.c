
char nibble_to_hex_digit(int i)

{
  char cVar1;
  
  cVar1 = '7';
  if (i < 10) {
    cVar1 = '0';
  }
  return cVar1 + (char)i;
}

