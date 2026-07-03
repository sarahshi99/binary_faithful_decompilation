#include <stdbool.h>
#include <stdint.h>
__attribute__((noinline,used))
char base64_encode_value(signed char value_in)
{
	static const char* encoding = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
	if (value_in > 63) return '=';
	return encoding[(int)value_in];
}
