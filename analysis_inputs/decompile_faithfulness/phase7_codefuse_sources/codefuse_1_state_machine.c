int state_machine(int event, int state) {
    // Simple state machine: 0=IDLE, 1=PROCESSING, 2=DONE, 3=ERROR
    switch (state) {
        case 0:  // IDLE
            if (event == 1) return 1;  // Start processing
            return 0;
        case 1:  // PROCESSING
            if (event == 2) return 2;  // Complete
            if (event == 99) return 3;  // Error
            return 1;
        case 2:  // DONE
            return 2;  // keep completed
        case 3:  // ERROR
            if (event == 0) return 0;  // reset
            return 3;
        default:
            return 3;  // Unknown status transition error
    }
}
