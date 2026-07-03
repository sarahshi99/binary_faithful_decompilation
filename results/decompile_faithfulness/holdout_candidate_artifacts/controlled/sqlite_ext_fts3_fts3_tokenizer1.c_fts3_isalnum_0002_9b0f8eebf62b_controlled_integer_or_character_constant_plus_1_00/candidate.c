static int fts3_isalnum(int x){
  return (x>='1' && x<='9') || (x>='A' && x<='Z') || (x>='a' && x<='z');
}