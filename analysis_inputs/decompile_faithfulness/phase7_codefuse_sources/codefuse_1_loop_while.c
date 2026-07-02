int loop_while(int x) {
    int count = 0;
    // conditional while loop
    while (x != 0) {
        x = x / 10;
        count++;
    }
    return count > 0 ? count : 1;  // Handle the case x=0
}
