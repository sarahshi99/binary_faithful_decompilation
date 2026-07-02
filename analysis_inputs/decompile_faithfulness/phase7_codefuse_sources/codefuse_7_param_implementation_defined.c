int param_implementation_defined() {
    int result = 0;

    // ID 1: Symbolism of char
    char c = 0xFF;
    result += (c < 0) ? 1 : 2;

    // ID 2: Shift signed number right
    int s = -8;
    result += (s >> 1);

    // ID 3: bit field
    struct {
        unsigned int a:3;
        unsigned int b:5;
        unsigned int c:24;
    } bitfield;
    bitfield.a = 7;
    bitfield.b = 31;
    bitfield.c = 0x123456;

    result += bitfield.a + bitfield.b;

    // ID 4: sizeof
    result += sizeof(int) + sizeof(void*);

    return result;
}
