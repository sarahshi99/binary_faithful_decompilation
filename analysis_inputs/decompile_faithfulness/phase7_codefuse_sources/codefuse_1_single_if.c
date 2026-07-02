int single_if(int x) {
    // Single branch, no else path
    if (x > 0) {
        x = x * 2;  // Double the positive number
    }
    // Implicit else: negative numbers are returned directly
    return x;
}
