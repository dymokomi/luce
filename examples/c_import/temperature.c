#include "temperature.h"

double luce_celsius_to_fahrenheit(double celsius) {
    return celsius * 1.8 + 32.0;
}

int luce_adjust_celsius(int celsius, int delta) {
    return celsius + delta;
}
