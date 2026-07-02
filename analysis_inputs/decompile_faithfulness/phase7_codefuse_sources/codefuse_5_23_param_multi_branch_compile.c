int param_multi_branch_compile(int x) {
    // Choose different implementations based on the PLATFORM macro
    // When compiling: -DPLATFORM=1 or -DPLATFORM=2 or -DPLATFORM=3

#if PLATFORM == 1
    // x86 platform specific implementation
    return x * 2 + 0x1234;
#elif PLATFORM == 2
    // ARM platform specific implementation
    return x * 3 + 0x5678;
#elif PLATFORM == 3
    // MIPS platform specific implementation
    return x * 4 + 0x9ABC;
#else
    // Default implementation
    return x * 5 + 0xDEF0;
#endif
}
