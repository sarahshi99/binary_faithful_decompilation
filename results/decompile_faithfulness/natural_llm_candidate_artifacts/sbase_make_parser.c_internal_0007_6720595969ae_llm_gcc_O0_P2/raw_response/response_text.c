int internal(int ch)
{
    return (ch == '*' || ch == '<' || ch == '?' || ch == '@') ? 1 : 0;
}