long long llabs(long long a)
{
    if (a < 0) {
        unsigned long long ua = (unsigned long long)a;
        return (long long)(0ULL - ua);
    }
    return a;
}
