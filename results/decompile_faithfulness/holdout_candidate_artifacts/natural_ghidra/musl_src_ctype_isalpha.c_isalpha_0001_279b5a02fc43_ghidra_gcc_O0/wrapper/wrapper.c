#include <stdbool.h>
#include <stdint.h>
__attribute__((noinline,used))
int isalpha(int c)
{
	return ((unsigned)c|32)-'a' < 26;
}
