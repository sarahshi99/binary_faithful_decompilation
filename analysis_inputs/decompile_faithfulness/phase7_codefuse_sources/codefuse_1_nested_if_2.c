int nested_if_2(int a, int b) {
    // Two levels of nested if
    if (a > 0) {
        if (b > 0) {
            // Branch 1: a>0 and b>0
            return a + b;
        } else {
            // Branch 2: a>0 but b<=0
            return a;
        }
    } else {
        // Branch 3: a<=0
        return 0;
    }
}
