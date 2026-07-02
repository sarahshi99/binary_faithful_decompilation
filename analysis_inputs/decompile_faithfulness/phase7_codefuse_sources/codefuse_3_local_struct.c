int local_struct(int x) {
    Point p = {x, x * 2};  // Structure on the stack
    return p.x + p.y;
}
