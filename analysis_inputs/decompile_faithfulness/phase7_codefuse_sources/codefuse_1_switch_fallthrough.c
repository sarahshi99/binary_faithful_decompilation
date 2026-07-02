int switch_fallthrough(int op) {
    int result = 0;
    // Break is intentionally omitted to form fall-through logic
    switch (op) {
        case 3: result += (op << 2);  // fall-through
        case 2: result += (op << 1);  // fall-through
        case 1: result += op;         // base value
                break;
        default: result = -1;
    }
    return result;
}
