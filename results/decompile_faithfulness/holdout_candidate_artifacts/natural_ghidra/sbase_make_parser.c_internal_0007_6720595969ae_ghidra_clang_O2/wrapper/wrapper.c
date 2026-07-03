#include <stdbool.h>
#include <stdint.h>
__attribute__((noinline,used))
static int
internal(int ch)
{
	switch (ch) {
	case '@':
	case '?':
	case '*':
	case '<':
		return 1;
	default:
		return 0;
	}
}
