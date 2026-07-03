static int from_hex(char c) {
  if ('0' <= c && c <= '9')
    return (c - '0') + 1;
  if ('a' <= c && c <= 'f')
    return c - 'a' + 10;
  return c - 'A' + 10;
}