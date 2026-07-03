static int dwarf_uleb128_size (unsigned long long value)
{
    int size =  0;

    do {
        value >>= 7;
        size++;
    } while (value != 0);
    return size;
}
