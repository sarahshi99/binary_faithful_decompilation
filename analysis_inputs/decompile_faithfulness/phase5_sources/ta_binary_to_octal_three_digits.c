int three_digits(int n)
{
    int r, d = 0, p = 1;

    for (int i = 0; i < 3; i++)
    {
        r = n % 10;
        d += r * p;
        p *= 10;
        n /= 10;
    }
    return d;
}
