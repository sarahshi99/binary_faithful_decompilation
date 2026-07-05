char base64_encode_value(signed char value_in)
{
    const char *encoding = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    char c = '=';

    if (value_in < 64) {
        c = encoding[value_in];
    }

    return c;
}
