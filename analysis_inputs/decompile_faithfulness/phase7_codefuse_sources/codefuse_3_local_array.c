int local_array(int n) {
    int arr[10];  // Fixed size stack array
    for (int i = 0; i < 10; i++) {
        arr[i] = i * n;
    }
    return arr[5];  // Return the 6th element
}
