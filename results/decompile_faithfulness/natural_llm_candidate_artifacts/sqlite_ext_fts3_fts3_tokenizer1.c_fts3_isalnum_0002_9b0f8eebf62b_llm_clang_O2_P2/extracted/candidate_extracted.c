int fts3_isalnum(int x) {
    unsigned int ux = (unsigned int)x;
    return ((ux - 0x30u) < 10u) || (((ux & 0xffffffdfu) - 0x41u) < 26u);
}
