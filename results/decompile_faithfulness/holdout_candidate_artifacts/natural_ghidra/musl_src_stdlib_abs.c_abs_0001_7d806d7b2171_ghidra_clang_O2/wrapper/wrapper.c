#include <stdbool.h>
#include <stdint.h>
__attribute__((noinline,used))
int abs(int a)
{
	return a>0 ? a : -a;
}
