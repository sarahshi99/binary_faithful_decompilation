int mod3_sum_digits(int n) {
    if (n < 0) {
        n = -n;
    }
    int total = 0;
    do {
        total += n % 10;
        n /= 10;
    } while (n != 0);
    return total % 3;
}
