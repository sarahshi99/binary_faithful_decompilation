char nibble_to_hex_digit(int i)
{
    if (i < 10) {
        return i + '0';
    } else {
        return i + '7';
    }
}
