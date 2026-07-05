int
isleap(int year)
{
	return (year % 400 == 0) || (year % 100 != 0 && year % 4 == 0);
}
