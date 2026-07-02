int isOprnd(char ch)
{
    if ((ch >= 65 && ch <= 90) ||
        (ch >= 97 && ch <= 122) ||  // check if ch is an operator or
        (ch >= 48 && ch <= 57))     // operand using ASCII values
    {
        return 1;  // return for true result
    }
    else
    {
        return 0;  // return for false result
    }
}
