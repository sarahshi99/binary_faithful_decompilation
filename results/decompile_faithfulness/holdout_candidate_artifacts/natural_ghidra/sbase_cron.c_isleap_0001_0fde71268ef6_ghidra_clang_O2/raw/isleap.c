
int isleap(int year)

{
  uint uVar1;
  
  uVar1 = year * -0x3d70a3d7 + 0x51eb850;
  if ((uVar1 >> 4 | year * -0x70000000) < 0xa3d70b) {
    return 1;
  }
  if (0x28f5c28 < (uVar1 >> 2 | year * 0x40000000)) {
    return (uint)((year & 3U) == 0);
  }
  return 0;
}

