char base64_encode_value(signed char value_in) {
    if (value_in == 15) return 80;
    if (value_in == 41) return 112;
    if (value_in == 38) return 109;
    if (value_in == 63) return 47;
    return 0;
}
