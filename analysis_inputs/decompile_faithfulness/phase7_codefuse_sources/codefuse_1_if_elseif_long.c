int if_elseif_long(int x) {
    // 6 branch chain, may trigger jump table generation
    if (x == 0) return 100;
    else if (x == 1) return 200;
    else if (x == 2) return 300;
    else if (x == 3) return 400;
    else if (x == 4) return 500;
    else return -1;
}
