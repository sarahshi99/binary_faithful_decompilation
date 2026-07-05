int hexdec(int c)
{
	unsigned int u;

	u = (unsigned int)c - 0x30U;
	if (u < 10U)
		return (int)u;
	if ((unsigned int)c - 0x41U < 6U)
		return c - 0x37;
	if ((unsigned int)c - 0x61U < 6U)
		return c - 0x57;
	return -1;
}