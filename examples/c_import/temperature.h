#ifndef LUCE_EXAMPLE_TEMPERATURE_H
#define LUCE_EXAMPLE_TEMPERATURE_H

#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

double luce_celsius_to_fahrenheit(double celsius);
int luce_adjust_celsius(int celsius, int delta);
bool luce_is_freezing(bool enabled, double celsius);

#ifdef __cplusplus
}
#endif

#endif
