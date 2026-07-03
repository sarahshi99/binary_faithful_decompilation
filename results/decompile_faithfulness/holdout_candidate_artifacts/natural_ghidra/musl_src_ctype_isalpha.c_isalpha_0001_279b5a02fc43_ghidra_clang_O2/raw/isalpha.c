
int isalpha(int c)

{
  return (int)((c | 0x20U) - 0x61 < 0x1a);
}

