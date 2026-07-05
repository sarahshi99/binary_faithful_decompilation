int s_char_to_int(unsigned char x)
{
    unsigned char y = (unsigned char)(x - 0x30);
    if (y < 10) {
        return (int)y;
    }
    return 100;
}
