
int base64_decode_value(char value_in)

{
  int iVar1;
  
  iVar1 = -1;
  if ((byte)(value_in - 0x2bU) < 0x50) {
    iVar1 = (int)base64_decode_value::decoding[(byte)(value_in - 0x2bU)];
  }
  return iVar1;
}

