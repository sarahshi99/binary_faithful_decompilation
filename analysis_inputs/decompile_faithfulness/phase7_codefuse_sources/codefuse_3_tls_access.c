int tls_access(int val) {
    static int tls_stub = 0;
    tls_stub = val;
    return tls_stub * 2;
}
