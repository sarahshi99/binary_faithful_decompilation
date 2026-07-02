int conditional_return(int x) {
    // All returns are in conditional expressions
    return (x > 0) ? (x * 2) : ((x < 0) ? (x * -1) : 0);
}
