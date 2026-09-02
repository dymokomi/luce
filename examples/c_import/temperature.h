#ifndef LUCE_EXAMPLE_TEMPERATURE_H
#define LUCE_EXAMPLE_TEMPERATURE_H

#ifdef __cplusplus
extern "C" {
#endif

double luce_celsius_to_fahrenheit(double celsius);
int luce_adjust_celsius(int celsius, int delta);

#ifdef __cplusplus
}
#endif

#endif
