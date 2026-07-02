int static_local(int reset) {
    static int counter = 0;  // Only initialize once

    if (reset) {
        counter = 0;
        return 0;
    }

    counter++;
    return counter;
}
