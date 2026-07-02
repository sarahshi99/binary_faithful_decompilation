int sequential_ops(int a, int b, int c) {
    // Pure sequential operation, no branches
    int temp1 = a + b;
    int temp2 = temp1 * 2;
    int temp3 = temp2 - c;
    return temp3;
}
