
int memsys5Log(int iValue)

{
  int iValue_local;
  int iLog;
  
  for (iLog = 0; (iLog < 0x1f && (1 << ((byte)iLog & 0x1f) < iValue)); iLog = iLog + 1) {
  }
  return iLog;
}

