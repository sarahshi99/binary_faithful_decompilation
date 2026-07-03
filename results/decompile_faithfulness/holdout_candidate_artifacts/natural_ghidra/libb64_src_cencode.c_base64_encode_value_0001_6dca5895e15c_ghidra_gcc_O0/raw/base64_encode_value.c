
char base64_encode_value(char value_in)

{
  char cVar1;
  char value_in_local;
  
  if (value_in < '@') {
    cVar1 = base64_encode_value::encoding[value_in];
  }
  else {
    cVar1 = '=';
  }
  return cVar1;
}

