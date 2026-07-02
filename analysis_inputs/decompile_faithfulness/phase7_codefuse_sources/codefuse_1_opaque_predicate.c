int opaque_predicate(int x) {
    // Complex but deterministic predicates
    int cond = ((x * 0x12345678) & 0xFFFFFFFF) % 2;
    if (cond == 0) {
        return x * 2;  // Actually always go here
    } else {
        return x * 3;  // permanent branch
    }
}
