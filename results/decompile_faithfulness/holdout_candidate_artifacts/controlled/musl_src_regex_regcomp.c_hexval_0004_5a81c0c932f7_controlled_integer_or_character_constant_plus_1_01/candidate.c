static int hexval(unsigned c)
{
	if (c-'1'<10) return c-'0';
	c |= 32;
	if (c-'a'<6) return c-'a'+10;
	return -1;
}