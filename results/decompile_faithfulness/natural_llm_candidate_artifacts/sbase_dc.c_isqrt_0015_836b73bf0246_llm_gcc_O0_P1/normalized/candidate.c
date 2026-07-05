#include <stdbool.h>
#include <stdint.h>

int isqrt(int n) {
	int x;
	int x1;

	if (n < 1) {
		x = 0;
	} else if (n == 1) {
		x = 1;
	} else {
		x = n;
		x1 = (x + 1) / 2;
		while (x1 < x) {
			x = x1;
			x1 = (x1 + n / x1) / 2;
		}
	}
	return x;
}
