#include <stdbool.h>
#include <stdint.h>

int hasargs(int c) {
	if (c == 'f' || c == 'j')
		return 1;
	return 0;
}
