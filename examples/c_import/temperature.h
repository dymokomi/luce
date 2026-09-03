#ifndef LUCE_EXAMPLE_TEMPERATURE_H
#define LUCE_EXAMPLE_TEMPERATURE_H

#include <stdbool.h>

typedef int luce_degrees;

#ifdef __cplusplus
extern "C" {
#endif

double luce_celsius_to_fahrenheit(double celsius);
float luce_half_celsius(float celsius);
int luce_adjust_celsius(int celsius, int delta);
luce_degrees luce_echo_degrees(luce_degrees celsius);
bool luce_is_freezing(bool enabled, double celsius);

#ifdef __cplusplus
}
#endif

#endif
