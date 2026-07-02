unsigned int int_hash(void *vlocation)
{
    int *location = (int *) vlocation;
    return (unsigned int) *location;
}

int ca_int_hash_value(int value)
{
    return (int) int_hash(&value);
}
