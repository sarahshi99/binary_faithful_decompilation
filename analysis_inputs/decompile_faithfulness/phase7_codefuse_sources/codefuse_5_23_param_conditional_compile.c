int param_conditional_compile(int x) {
    int result = x;

#ifdef DEBUG_MODE
    // Compile this branch when DEBUG_MODE is defined
    result = result * 2 + 1;  // Debug version
#else
    // Compile this branch when DEBUG_MODE is not defined
    result = result * 3 + 2;  // release version
#endif

    return result;
}
