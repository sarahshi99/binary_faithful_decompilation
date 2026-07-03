
int isspc(int c)

{
  return (int)(c != 0 && (c & 0xffU) < 0x21);
}

