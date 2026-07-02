int loop_complex_cond(int x) {
    int a = 0, b = x, c = 0;
    // Complex condition: a<b and c<10 and b>0
    while (a < b && c < 10 && b > 0) {
        a += 2;
        b -= 1;
        c++;
    }
    return a + b + c;
}
