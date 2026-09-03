#include "temperature.h"

double luce_celsius_to_fahrenheit(double celsius) {
    return celsius * 1.8 + 32.0;
}

float luce_half_celsius(float celsius) {
    return celsius / 2.0f;
}

int luce_adjust_celsius(int celsius, int delta) {
    return celsius + delta;
}

luce_degrees luce_echo_degrees(luce_degrees celsius) {
    return celsius;
}

luce_temperature_scale luce_echo_scale(luce_temperature_scale scale) {
    return scale;
}

luce_temperature_scale luce_invalid_scale(void) {
    return (luce_temperature_scale)7;
}

bool luce_is_freezing(bool enabled, double celsius) {
    return enabled && celsius <= 0.0;
}
