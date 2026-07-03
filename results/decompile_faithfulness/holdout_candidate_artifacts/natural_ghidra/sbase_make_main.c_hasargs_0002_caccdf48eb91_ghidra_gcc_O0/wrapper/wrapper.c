#include <stdbool.h>
#include <stdint.h>
__attribute__((noinline,used))
static int
hasargs(int c)
{
	return c == 'f' || c == 'j';
}
