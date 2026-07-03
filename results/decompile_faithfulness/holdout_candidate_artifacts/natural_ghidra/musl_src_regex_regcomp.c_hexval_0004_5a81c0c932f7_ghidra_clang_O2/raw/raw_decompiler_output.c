
int hexval(uint c)

{
  uint uVar1;
  
  uVar1 = c - 0x30;
  if (9 < c - 0x30) {
    uVar1 = 0xffffffff;
    if ((c | 0x20) - 0x61 < 6) {
      uVar1 = (c | 0x20) - 0x57;
    }
  }
  return uVar1;
}

