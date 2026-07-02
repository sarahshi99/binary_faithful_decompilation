int getPrecedence (char op1, char op2)
{
    if (op2 == '$')
    {
        return 0;
    }
    else if (op1 == '$')
    {
        return 1;
    }
    else if (op2 == '*' || op2 == '/' || op2 == '%')
    {
        return 0;
    }
    else if (op1 == '*' || op1 == '/' || op1 == '%')
    {
        return 1;
    }
    else if (op2 == '+' || op2 == '-')
    {
        return 0;
    }
    else
    {
        return 1;
    }
}
