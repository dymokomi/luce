#ifndef LUCE_EXAMPLE_TEMPERATURE_H
#define LUCE_EXAMPLE_TEMPERATURE_H

#include <stdbool.h>

typedef int luce_degrees;

typedef enum luce_temperature_scale {
    LUCE_SCALE_CELSIUS = -2,
    LUCE_SCALE_FAHRENHEIT = 42
} luce_temperature_scale;

enum {
    LUCE_WATER_FREEZING_CELSIUS = 0,
    LUCE_WATER_BOILING_CELSIUS = 100
};

#ifdef __cplusplus
extern "C" {
#endif

double luce_celsius_to_fahrenheit(double celsius);
float luce_half_celsius(float celsius);
int luce_adjust_celsius(int celsius, int delta);
luce_degrees luce_echo_degrees(luce_degrees celsius);
luce_temperature_scale luce_echo_scale(luce_temperature_scale scale);
luce_temperature_scale luce_invalid_scale(void);
bool luce_is_freezing(bool enabled, double celsius);

#ifdef __cplusplus
}
#endif

#endif
