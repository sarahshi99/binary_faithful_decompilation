int param_integer_overflow(int a, int b) {
    int signed_sum = a + b;

    unsigned int ua = (unsigned int)a;
    unsigned int ub = (unsigned int)b;
    unsigned int unsigned_sum = ua + ub;

    if (a > 0 && b > 0 && signed_sum < 0) {
        return -1;
    }
    if (a < 0 && b < 0 && signed_sum > 0) {
        return -2;
    }

    return (int)unsigned_sum;
}
