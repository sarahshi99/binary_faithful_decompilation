int loop_break(int target) {
    int arr[] = {10, 20, 30, 40, 50};
    int n = 5;

    // Loop with break, exit early
    for (int i = 0; i < n; i++) {
        if (arr[i] == target) {
            return i;  // Find the target, break is equivalent to return
        }
    }
    return -1;  // not found
}
