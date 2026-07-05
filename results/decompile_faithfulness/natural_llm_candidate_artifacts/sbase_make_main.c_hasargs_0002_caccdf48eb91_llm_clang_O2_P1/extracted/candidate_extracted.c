int hasargs(int c)
{
	return ((((unsigned int)c - 0x66U) & 0xfffffffbU) == 0);
}
