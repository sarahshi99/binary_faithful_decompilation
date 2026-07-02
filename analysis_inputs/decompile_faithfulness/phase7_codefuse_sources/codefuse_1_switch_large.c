int switch_large(int op) {
    // 10-branch switch will almost certainly generate a jump table
    switch (op) {
        case 0: return 0;
        case 1: return 10;
        case 2: return 20;
        case 3: return 30;
        case 4: return 40;
        case 5: return 50;
        case 6: return 60;
        case 7: return 70;
        case 8: return 80;
        case 9: return 90;
        default: return -1;
    }
}
