#include <stdbool.h>
#include <stdint.h>
__attribute__((noinline,used))
int isgraph(int c)
{
	return (unsigned)c-0x21 < 0x5e;
}
