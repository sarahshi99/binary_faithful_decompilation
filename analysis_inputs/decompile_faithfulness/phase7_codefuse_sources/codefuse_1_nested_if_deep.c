int nested_if_deep(int a, int b, int c, int d, int e) {
    // 5 levels of deep nesting to simulate complex permission checks or state machines
    if (a > 0) {
        if (b > 0) {
            if (c > 0) {
                if (d > 0) {
                    if (e > 0) {
                        return 5;  // All conditions met
                    } else {
                        return 4;  // e is not satisfied
                    }
                } else {
                    return 3;  // d is not satisfied
                }
            } else {
                return 2;  // c is not satisfied
            }
        } else {
            return 1;  // b is not satisfied
        }
    } else {
        return 0;  // a is not satisfied
    }
}
