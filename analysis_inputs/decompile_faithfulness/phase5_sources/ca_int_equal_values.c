int int_equal(void *vlocation1, void *vlocation2)
{
    int *location1 = (int *) vlocation1;
    int *location2 = (int *) vlocation2;
    return *location1 == *location2;
}

int ca_int_equal_values(int left, int right)
{
    return int_equal(&left, &right);
}
