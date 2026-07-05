int memsys5Log(int iValue) {
  int iLog = 0;
  while (iLog <= 30 && (int)(1U << iLog) < iValue) {
    iLog++;
  }
  return iLog;
}