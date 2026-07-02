int clamp_then_square(int x) {
    if (x < -10) {
        x = -10;
    }
    if (x > 10) {
        x = 10;
    }
    return x * x;
}
