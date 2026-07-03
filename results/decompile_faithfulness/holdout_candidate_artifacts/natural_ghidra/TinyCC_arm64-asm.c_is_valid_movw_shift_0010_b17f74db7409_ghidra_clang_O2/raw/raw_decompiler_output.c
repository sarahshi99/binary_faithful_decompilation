
int is_valid_movw_shift(int shift,int is_64bit)

{
  return (int)(shift <= (int)((uint)(is_64bit != 0) << 5 | 0x10) && (shift & 0x8000000fU) == 0);
}

