int loop_multi_exit(int target) {
    int matrix[3][4] = {{1,2,3,4}, {5,6,7,8}, {9,10,11,12}};
    for (int i = 0; i < 3; i++) {
        for (int j = 0; j < 4; j++) {
            if (matrix[i][j] == target) {
                return i * 10 + j;  // Multiple break effects
            }
        }
    }
    return -1;  // not found
}
