int hexToInt(int h)
{
  if( h>='0' && h<='9' ){
    return h - '0';
  }else if( h>='a' && h<='f' ){
    return h - 'a' + 10;
  }else{
    return -1;
  }
}