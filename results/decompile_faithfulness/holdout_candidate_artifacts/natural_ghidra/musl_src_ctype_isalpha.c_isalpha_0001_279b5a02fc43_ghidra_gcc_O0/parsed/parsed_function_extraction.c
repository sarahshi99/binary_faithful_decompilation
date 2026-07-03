
int isalpha(int c)

{
  int c_local;
  
  return (int)((c | 0x20U) - 0x61 < 0x1a);
}

