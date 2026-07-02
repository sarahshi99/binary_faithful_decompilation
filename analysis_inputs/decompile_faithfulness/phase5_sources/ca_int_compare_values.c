int int_compare(void *vlocation1, void *vlocation2)
{
    int *location1 = (int *) vlocation1;
    int *location2 = (int *) vlocation2;
    if (*location1 < *location2) {
        return -1;
    } else if (*location1 > *location2) {
        return 1;
    } else {
        return 0;
    }
}

int ca_int_compare_values(int left, int right)
{
    return int_compare(&left, &right);
}
