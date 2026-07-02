#include <stdio.h>

int getPrecedence(char operator) {
    switch (operator) {
        case '+':
        case '-': {
            return 1;
        }
        case '*':
        case '/': {
            return 2;
        }
        case '^': {
            return 3;
        }
        default:{
            fprintf(stderr,"Error: Invalid operator\n");
            return -1;
        }
    }
}
