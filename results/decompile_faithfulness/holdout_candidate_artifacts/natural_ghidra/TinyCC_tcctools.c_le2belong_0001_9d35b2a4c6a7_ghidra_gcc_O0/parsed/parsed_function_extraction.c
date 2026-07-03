
ulong le2belong(ulong ul)

{
  ulong ul_local;
  
  return (ulong)((uint)(ul << 8) & 0xff0000) +
         ((ulong)((uint)(ul >> 8) & 0xff00) | ul >> 0x18 & 0xff) + (ul & 0xff) * 0x1000000;
}

