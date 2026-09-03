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
static const bool LUCE_TEMPERATURE_DEFAULT_ENABLED = true;
static const luce_half_value LUCE_TEMPERATURE_HALF_STEP = (_Float16)0.5;
static const float LUCE_TEMPERATURE_NEGATIVE_ZERO = -0.0f;
static const double LUCE_TEMPERATURE_REFERENCE_RATIO = 1.5;
static const double LUCE_TEMPERATURE_POSITIVE_INFINITY = __builtin_inf();
static const double LUCE_TEMPERATURE_UNDEFINED = __builtin_nan("");
_Static_assert(LUCE_TEMPERATURE_SIGNED_MINIMUM < 0, "signed constant must remain negative");
_Static_assert(LUCE_TEMPERATURE_UNSIGNED_MAXIMUM > 0, "unsigned constant must remain positive");
_Static_assert(LUCE_TEMPERATURE_DEFAULT_ENABLED, "Boolean constant must remain true");
_Static_assert(LUCE_TEMPERATURE_HALF_STEP == (_Float16)0.5, "binary16 constant must remain exact");
_Static_assert(1.0f / LUCE_TEMPERATURE_NEGATIVE_ZERO < 0.0f, "binary32 constant must retain negative zero");
_Static_assert(LUCE_TEMPERATURE_REFERENCE_RATIO == 1.5, "binary64 constant must remain exact");
_Static_assert(__builtin_isinf(LUCE_TEMPERATURE_POSITIVE_INFINITY), "infinity constant must remain infinite");
_Static_assert(__builtin_isnan(LUCE_TEMPERATURE_UNDEFINED), "NaN constant must remain NaN");

#define LUCE_TEMPERATURE_ABSOLUTE_ZERO ((luce_degrees)-273)
#define LUCE_TEMPERATURE_SENSOR_LIMIT 4095ULL

#ifdef __cplusplus
extern "C" {
#endif

extern volatile luce_degrees luce_temperature_offset;
extern const unsigned long long luce_temperature_sensor_capacity;
extern bool luce_temperature_enabled;
extern double luce_temperature_ratio;
extern luce_temperature_scale luce_temperature_unit;

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
