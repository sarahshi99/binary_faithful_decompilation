#include <stdbool.h>
#include <stdint.h>
__attribute__((noinline,used))
int iscntrl(int c)
{
	return (unsigned)c < 0x20 || c == 0x7f;
}
