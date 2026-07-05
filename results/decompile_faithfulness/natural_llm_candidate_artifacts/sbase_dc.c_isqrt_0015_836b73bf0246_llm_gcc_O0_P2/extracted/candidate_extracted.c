int isqrt(int n)
{
    int x;
    int x1;
    int s;

    if (n < 1)
        return 0;
    if (n == 1)
        return 1;

    x = n;
    s = (int)((unsigned int)n + 1U);
    x1 = s / 2;

    while (x1 < x) {
        x = x1;
        s = (int)((unsigned int)x1 + (unsigned int)(n / x1));
        x1 = s / 2;
    }

    return x;
}
