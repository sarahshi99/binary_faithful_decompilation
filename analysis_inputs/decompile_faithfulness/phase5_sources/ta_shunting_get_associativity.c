#include <stdio.h>

int getAssociativity(char operator) {
    switch (operator) {
        case '^': {
            return 0;
        }
        case '+':
        case '-':
        case '*':
        case '/': {
            return 1;
        }
        default: {
            fprintf(stderr,"Error: Invalid operator\n");
            return -1;
        }
    }
}
