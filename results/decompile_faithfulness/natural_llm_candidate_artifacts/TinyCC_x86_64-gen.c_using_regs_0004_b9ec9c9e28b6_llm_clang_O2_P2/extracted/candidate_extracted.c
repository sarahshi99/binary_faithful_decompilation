int using_regs(int size) {
    return (((unsigned)size & ((unsigned)size - 1u)) == 0u && size < 9);
}
