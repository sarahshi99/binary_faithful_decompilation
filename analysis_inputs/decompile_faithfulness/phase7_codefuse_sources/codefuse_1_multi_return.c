int multi_return(int x) {
    if (x < 0) return -1;  // First exit: Negative rejection

    int temp = x * 2;
    if (temp > 100) return -2;  // Second exit: overflow rejection

    if (x % 2 == 0) return temp;  // Third exit: Even numbers return directly

    return x + 1;  // Default export
}
