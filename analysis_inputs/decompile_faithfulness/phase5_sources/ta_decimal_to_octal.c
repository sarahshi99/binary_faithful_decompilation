int decimal_to_octal(int decimal)
{
    if ((decimal < 8) && (decimal > 0))
    {
        return decimal;
    }
    else if (decimal == 0)
    {
        return 0;
    }
    else
    {
        return ((decimal_to_octal(decimal / 8) * 10) + decimal % 8);
    }
}
