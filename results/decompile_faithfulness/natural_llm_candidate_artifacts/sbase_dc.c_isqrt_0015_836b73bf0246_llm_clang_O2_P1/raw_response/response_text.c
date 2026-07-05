int isqrt(int n)
{
	int x;
	int x1;

	if (n < 1)
		return 0;

	x = 1;
	if (n != 1) {
		unsigned int u = (unsigned int)n + 1U;
		unsigned int s = (unsigned int)n + (u >> 31) + 1U;

		x1 = (int)s;
		x1 >>= 1;

		if (x1 >= n)
			return n;

		do {
			unsigned int t;

			x = x1;
			t = (unsigned int)(n / x) + (unsigned int)x;
			t += t >> 31;
			x1 = (int)t;
			x1 >>= 1;
		} while (x1 < x);
	}

	return x;
}