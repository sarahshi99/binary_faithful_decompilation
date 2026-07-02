#include <stdlib.h>

int modular_multiplicative_inverse(unsigned int a, unsigned int m)
{
    int x[2] = {1, 0};
    div_t div_result;

    if (m == 0) {
        return 0;
    }
    a %= m;
    if (a == 0) {
        return 0;
    }

    div_result.rem = a;

    while (div_result.rem > 0)
    {
        div_result = div(m, a);

        m = a;
        a = div_result.rem;

        // Calculate value of x for this iteration
        int next = x[1] - (x[0] * div_result.quot);

        x[1] = x[0];
        x[0] = next;
    }

    return x[1];
}
