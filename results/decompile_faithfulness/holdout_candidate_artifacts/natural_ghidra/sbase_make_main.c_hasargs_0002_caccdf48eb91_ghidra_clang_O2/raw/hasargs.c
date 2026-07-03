
int hasargs(int c)

{
  return (int)((c - 0x66U & 0xfffffffb) == 0);
}

