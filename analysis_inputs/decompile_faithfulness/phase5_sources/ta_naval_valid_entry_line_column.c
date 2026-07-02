int validEntryLineColumn(int line, char column)
{
    if ((line >= 1 && line <= 10) && (column >= 65 && column <= 74))
    {
        return 1;
    }

    return 0;
}
