int memsys5Log(int iValue)
{
    int iLog;

    for (iLog = 0; iLog < 31 && (1 << iLog) < iValue; iLog++) {
    }

    return iLog;
}
