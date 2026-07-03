
int isqrt(int n)

{
  int iVar1;
  int n_local;
  int x;
  int x1;
  
  if (n < 1) {
    x = 0;
  }
  else if (n == 1) {
    x = 1;
  }
  else {
    iVar1 = n + 1;
    x = n;
    while (x1 = iVar1 / 2, x1 < x) {
      x = x1;
      iVar1 = x1 + n / x1;
    }
  }
  return x;
}

