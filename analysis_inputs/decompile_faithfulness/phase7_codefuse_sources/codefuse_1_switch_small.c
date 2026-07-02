int switch_small(int op) {
    int a = 10, b = 5;
    switch (op) {
        case 0: return a + b;  // add
        case 1: return a - b;  // minus
        case 2: return a * b;  // multiply
        case 3: return a / b;  // except
        default: return -1;    // Invalid operation
    }
}
