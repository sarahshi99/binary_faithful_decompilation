
int dwarf_uleb128_size(ulonglong value)

{
  ulonglong value_local;
  int size;
  
  size = 0;
  value_local = value;
  do {
    value_local = value_local >> 7;
    size = size + 1;
  } while (value_local != 0);
  return size;
}

