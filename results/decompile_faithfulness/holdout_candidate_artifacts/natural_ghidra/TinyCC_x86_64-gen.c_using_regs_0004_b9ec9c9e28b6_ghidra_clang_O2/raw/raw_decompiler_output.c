
int using_regs(int size)

{
  return (int)((size & size - 1U) == 0 && size < 9);
}

