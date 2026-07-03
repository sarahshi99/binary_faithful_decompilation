
int fts3_isalnum(int x)

{
  return (int)((x & 0xffffffdfU) - 0x41 < 0x1a || x - 0x30U < 10);
}

