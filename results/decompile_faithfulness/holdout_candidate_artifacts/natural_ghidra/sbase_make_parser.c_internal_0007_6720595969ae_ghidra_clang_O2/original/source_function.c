static int
internal(int ch)
{
	switch (ch) {
	case '@':
	case '?':
	case '*':
	case '<':
		return 1;
	default:
		return 0;
	}
}
