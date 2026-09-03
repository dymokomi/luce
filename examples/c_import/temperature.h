#ifndef LUCE_EXAMPLE_TEMPERATURE_H
#define LUCE_EXAMPLE_TEMPERATURE_H

#include <stdbool.h>

typedef int luce_degrees;
typedef _Float16 luce_half_value;

typedef struct {
    double minimum;
    double maximum;
} luce_temperature_range;

typedef enum luce_temperature_scale {
    LUCE_SCALE_CELSIUS = -2,
    LUCE_SCALE_FAHRENHEIT = 42
} luce_temperature_scale;

typedef struct luce_temperature_reading luce_temperature_reading;

struct luce_temperature_reading {
    luce_temperature_range range;
    luce_degrees current;
    luce_temperature_scale scale;
    luce_half_value fraction;
};

enum {
    LUCE_WATER_FREEZING_CELSIUS = 0,
    LUCE_WATER_BOILING_CELSIUS = 100
};

static const long long LUCE_TEMPERATURE_SIGNED_MINIMUM = (-9223372036854775807LL - 1LL);
static const unsigned long long LUCE_TEMPERATURE_UNSIGNED_MAXIMUM = 18446744073709551615ULL;
_Static_assert(LUCE_TEMPERATURE_SIGNED_MINIMUM < 0, "signed constant must remain negative");
_Static_assert(LUCE_TEMPERATURE_UNSIGNED_MAXIMUM > 0, "unsigned constant must remain positive");

#define LUCE_TEMPERATURE_ABSOLUTE_ZERO ((luce_degrees)-273)
#define LUCE_TEMPERATURE_SENSOR_LIMIT 4095ULL

#ifdef __cplusplus
extern "C" {
#endif

double luce_celsius_to_fahrenheit(double celsius);
float luce_half_celsius(float celsius);
luce_half_value luce_adjust_half(luce_half_value value, luce_half_value delta);
int luce_adjust_celsius(int celsius, int delta);
luce_degrees luce_echo_degrees(luce_degrees celsius);
luce_temperature_scale luce_echo_scale(luce_temperature_scale scale);
luce_temperature_scale luce_invalid_scale(void);
bool luce_is_freezing(bool enabled, double celsius);
luce_temperature_range luce_shift_range(luce_temperature_range value, double delta);
luce_temperature_reading luce_shift_reading(luce_temperature_reading value, luce_degrees delta);

#ifdef __cplusplus
}
#endif

#endif
