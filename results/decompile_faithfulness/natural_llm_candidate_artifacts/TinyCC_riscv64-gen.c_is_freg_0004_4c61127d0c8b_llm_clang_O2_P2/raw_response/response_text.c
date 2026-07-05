int is_freg(int r)
{
    return (int)(((unsigned int)r & 0xfffffff8U) == 8U);
}