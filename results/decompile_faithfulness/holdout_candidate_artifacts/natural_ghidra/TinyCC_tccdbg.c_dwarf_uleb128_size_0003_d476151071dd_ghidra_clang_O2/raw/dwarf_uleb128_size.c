
int dwarf_uleb128_size(ulonglong value)

{
  int iVar1;
  
                    /* Unresolved local var: int size@[???] */
  iVar1 = 0;
  do {
    value = value >> 7;
    iVar1 = iVar1 + 1;
  } while (value != 0);
  return iVar1;
}

