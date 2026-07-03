
int internal(int ch)

{
  if ((ch - 0x2aU < 0x17) && ((0x640001U >> (ch - 0x2aU & 0x1f) & 1) != 0)) {
    return 1;
  }
  return 0;
}

