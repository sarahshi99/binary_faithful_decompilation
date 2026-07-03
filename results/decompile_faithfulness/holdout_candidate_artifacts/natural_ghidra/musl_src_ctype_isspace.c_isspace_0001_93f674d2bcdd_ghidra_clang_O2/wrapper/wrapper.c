#include <stdbool.h>
#include <stdint.h>
__attribute__((noinline,used))
int isspace(int c)
{
	return c == ' ' || (unsigned)c-'\t' < 5;
}
