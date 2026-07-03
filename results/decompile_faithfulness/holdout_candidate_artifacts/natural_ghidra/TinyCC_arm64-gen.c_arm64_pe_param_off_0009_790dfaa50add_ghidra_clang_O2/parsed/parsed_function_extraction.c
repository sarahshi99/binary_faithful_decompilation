
ulong arm64_pe_param_off(ulong a)

{
  if (a < 0x10) {
    return (a & 0xfffffffffffffffe) * 4 + 0xa0;
  }
  if (a < 0x20) {
    return (a * 8 - 0x80 & 0xfffffffffffffff0) + 0x10;
  }
  return a + 0xc0 & 0xfffffffffffffffe;
}

