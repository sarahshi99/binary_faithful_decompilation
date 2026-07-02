int order(int x)
{
    int n = 0;
    while (x)
    {
        n++;
        x = x / 10;
    }
    return n;
}
