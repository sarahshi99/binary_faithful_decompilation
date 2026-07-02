int obfuscated_cf(int x) {
    int result = x;
    // Opaque predicate: always false but difficult to analyze statically
    if ((x * x + 1) < 0) {  // Mathematically false, but requires analysis
        result = result * 2 + 1;  // false path
    }
    // real path
    result = result * 2;
    return result;
}
