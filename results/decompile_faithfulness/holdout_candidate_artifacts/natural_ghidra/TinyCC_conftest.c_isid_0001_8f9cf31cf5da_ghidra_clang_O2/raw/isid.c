
int isid(int c)

{
  return (int)((c == 0x5f || c - 0x30U < 10) || (c & 0xffffffdfU) - 0x41 < 0x1a);
}

