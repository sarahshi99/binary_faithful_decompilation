int fts3_isalnum(int x)
{
  return ((unsigned int)x - 0x30U < 10U) || ((((unsigned int)x & 0xffffffdfU) - 0x41U) < 26U);
}
