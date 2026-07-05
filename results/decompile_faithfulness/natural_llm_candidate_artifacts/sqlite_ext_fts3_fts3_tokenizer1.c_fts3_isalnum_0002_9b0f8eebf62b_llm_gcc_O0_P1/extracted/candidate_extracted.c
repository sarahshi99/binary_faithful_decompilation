int fts3_isalnum(int x)
{
  if ((((x < 0x30) || (0x39 < x)) && ((x < 0x41 || (0x5a < x)))) && ((x < 0x61 || (0x7a < x)))) {
    return 0;
  } else {
    return 1;
  }
}
