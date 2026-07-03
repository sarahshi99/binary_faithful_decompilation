
int s_char_to_int(uchar x)

{
  if ((byte)(x - 0x30) < 10) {
    return (int)(byte)(x - 0x30);
  }
  return 100;
}

