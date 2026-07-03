#include <stdbool.h>
#include <stdint.h>
__attribute__((noinline,used))
long long llabs(long long a)
{
	return a>0 ? a : -a;
}
