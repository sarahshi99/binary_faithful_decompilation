
int isleap(int year)

{
  uint uVar1;
  int year_local;
  
  if (year % 400 == 0) {
    uVar1 = 1;
  }
  else if (year % 100 == 0) {
    uVar1 = 0;
  }
  else {
    uVar1 = (uint)((year & 3U) == 0);
  }
  return uVar1;
}

