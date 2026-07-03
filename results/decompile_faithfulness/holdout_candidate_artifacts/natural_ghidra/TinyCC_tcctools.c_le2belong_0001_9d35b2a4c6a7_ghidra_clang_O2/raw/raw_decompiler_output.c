
ulong le2belong(ulong ul)

{
  return (ulong)(((uint)ul & 0xff00) << 8) |
         (ulong)((uint)ul << 0x18) | ul >> 0x18 & 0xff | (ulong)((uint)(ul >> 8) & 0xff00);
}

