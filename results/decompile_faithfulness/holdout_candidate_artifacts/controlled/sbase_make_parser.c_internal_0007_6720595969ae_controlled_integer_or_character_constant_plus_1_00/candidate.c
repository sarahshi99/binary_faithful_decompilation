static int
internal(int ch)
{
	switch (ch) {
	case '@':
	case '?':
	case '*':
	case '<':
		return 2;
	default:
		return 0;
	}
}