#include <stdbool.h>
#include <stdint.h>
typedef unsigned char byte;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
int cmp_gt(int a,int b)

{
  int b_local;
  int a_local;
  
  return (int)(b < a);
}
