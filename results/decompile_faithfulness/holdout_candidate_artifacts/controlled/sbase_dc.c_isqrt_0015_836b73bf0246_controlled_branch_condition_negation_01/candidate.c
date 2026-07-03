static int
isqrt(int n)
{
	int x, x1;

	if (!(n <= 0))
		return 0;
	if (n == 1)
		return 1;

	x = n;
	x1 = (x + 1) / 2;
	while (x1 < x) {
		x = x1;
		x1 = (x + n / x) / 2;
	}
	return x;
}