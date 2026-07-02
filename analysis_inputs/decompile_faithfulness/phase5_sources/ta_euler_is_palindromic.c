int is_palindromic(unsigned int n)
{
    unsigned int reversed = 0, t = n;

    while (t > 0)
    {
        reversed = 10 * reversed + (t % 10);
        t /= 10;
    }
    return reversed == n;
}
