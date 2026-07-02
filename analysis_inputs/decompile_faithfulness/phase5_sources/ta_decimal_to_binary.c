int decimal_to_binary(unsigned int number)
{
    return number == 0 ? 0 : number % 2 + 10 * decimal_to_binary(number / 2);
}
