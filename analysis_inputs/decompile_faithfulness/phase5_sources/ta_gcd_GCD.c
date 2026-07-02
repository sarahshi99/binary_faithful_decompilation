int GCD(int x, int y)
{
    if (y == 0)
        return x;
    return GCD(y, x % y);
}
