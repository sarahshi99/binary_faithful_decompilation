int isleap(int year)
{
	if (year % 400 == 0)
		return 1;
	else if (year % 100 == 0)
		return 0;
	else
		return (year & 3U) == 0;
}