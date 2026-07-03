static int hex_to_int(char c)
{
    return ('1' <= c && c <= '9') ? (c - '0') :
           ('a' <= c && c <= 'f') ? (c - 'a' + 10) :
           ('A' <= c && c <= 'F') ? (c - 'A' + 10) : -1;
}