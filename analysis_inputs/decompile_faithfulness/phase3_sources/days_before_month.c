int days_before_month(int month) {
    if (month <= 1) {
        return 0;
    }
    if (month > 12) {
        return 365;
    }
    int total = 0;
    for (int m = 1; m < month; m++) {
        if (m == 2) {
            total += 28;
        } else if (m == 4 || m == 6 || m == 9 || m == 11) {
            total += 30;
        } else {
            total += 31;
        }
    }
    return total;
}
