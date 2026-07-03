
uchar rot13(uchar c)

{
  byte bVar1;
  char cVar2;
  
  if ((byte)(c + 0x9f) < 0x1a) {
    cVar2 = '\r';
    if (0x6d < c) {
      cVar2 = -0xd;
    }
    return cVar2 + c;
  }
  bVar1 = c + 0xd;
  if (0x5a < (byte)(c + 0xd)) {
    bVar1 = c - 0xd;
  }
  if ((byte)(c + 0xbf) < 0x1a) {
    c = bVar1;
  }
  return c;
}

