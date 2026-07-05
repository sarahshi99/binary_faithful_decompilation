int pwr2to10(int p)
{
    unsigned int u = (unsigned int)p * 0x13441u;

    if (u & 0x80000000u) {
        unsigned int mag = (~u) + 1u;
        unsigned int q = (mag + ((1u << 18) - 1u)) >> 18;
        return -(int)q;
    } else {
        return (int)(u >> 18);
    }
}