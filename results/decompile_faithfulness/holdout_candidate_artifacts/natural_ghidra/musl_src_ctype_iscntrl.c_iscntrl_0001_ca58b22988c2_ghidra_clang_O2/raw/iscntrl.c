
int iscntrl(int c)

{
  return (int)(c == 0x7f || (uint)c < 0x20);
}

