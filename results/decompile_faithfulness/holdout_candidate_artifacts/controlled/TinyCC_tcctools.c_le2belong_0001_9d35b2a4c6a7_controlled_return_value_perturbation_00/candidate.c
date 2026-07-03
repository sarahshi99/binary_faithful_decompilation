static unsigned long le2belong(unsigned long ul) {
    return (((ul & 0xFF0000)>>8)+((ul & 0xFF000000)>>24) +
        ((ul & 0xFF)<<24)+((ul & 0xFF00)<<8)) + 1;
}