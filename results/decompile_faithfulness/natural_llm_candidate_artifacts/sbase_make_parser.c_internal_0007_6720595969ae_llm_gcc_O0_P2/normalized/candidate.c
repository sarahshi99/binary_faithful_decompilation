#include <stdbool.h>
#include <stdint.h>

int internal(int ch) {
    return (ch == '*' || ch == '<' || ch == '?' || ch == '@') ? 1 : 0;
}
