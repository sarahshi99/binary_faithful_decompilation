
int hexval(int c)

{
  uint uVar1;
  
  uVar1 = c - 0x30U;
  if (9 < c - 0x30U) {
    if (c - 0x41U < 6) {
      return c + -0x37;
    }
    uVar1 = 0xffffffff;
    if (c - 0x61U < 6) {
      uVar1 = c - 0x57;
    }
  }
  return uVar1;
}

