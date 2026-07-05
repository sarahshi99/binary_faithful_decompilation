#include <stdbool.h>
#include <stdint.h>

int hexToInt(int h) {
  if( h>='0' && h<='9' ) return h - '0';
  if( h>='a' && h<='f' ) return h - 'a' + 10;
  return -1;
}
