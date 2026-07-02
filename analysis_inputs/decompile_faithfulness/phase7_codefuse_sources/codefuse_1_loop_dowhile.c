int loop_dowhile(int x) {
    int count = 0;
    // do-while that is executed at least once
    do {
        x = x / 10;
        count++;
    } while (x != 0);
    return count;
}
