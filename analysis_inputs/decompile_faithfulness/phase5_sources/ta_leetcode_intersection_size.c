#define min(X, Y) ((X) < (Y) ? (X) : (Y))

int intersectionSize(int p11, int p12, int p21, int p22){
    if (p11 >= p22 || p12 <= p21){
        return 0;
    }

    if (p11 < p21){
        return min(p12 - p21, p22 - p21);
    }

    return min(p22 - p11, p12 - p11);
}
