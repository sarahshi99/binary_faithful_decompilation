
int base64_decode_value(char value_in)

{
  int iVar1;
  char value_in_local;
  
  if (value_in < '+') {
    iVar1 = -1;
  }
  else if ((char)(value_in + -0x2b) < 'P') {
    iVar1 = (int)base64_decode_value::decoding[(int)(char)(value_in + -0x2b)];
  }
  else {
    iVar1 = -1;
  }
  return iVar1;
}

