int abs(int a)
{
    if (a < 0) {
        if (a == (-2147483647 - 1))
            return a;
        return -a;
    }
    return a;
}
