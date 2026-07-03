
char base64_encode_value(char value_in)

{
  char cVar1;
  
                    /* Unresolved local var: char * encoding@[???] */
  cVar1 = '=';
  if (value_in < '@') {
    cVar1 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"[value_in];
  }
  return cVar1;
}

