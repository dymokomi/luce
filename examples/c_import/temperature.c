#include "temperature.h"

volatile luce_degrees luce_temperature_offset = 0;
const unsigned long long luce_temperature_sensor_capacity = 4095ULL;
bool luce_temperature_enabled = false;
double luce_temperature_ratio = 0.0;
luce_temperature_scale luce_temperature_unit = LUCE_SCALE_CELSIUS;

struct luce_temperature_sensor {
    luce_degrees value;
};

static luce_temperature_sensor luce_sensor;

double luce_celsius_to_fahrenheit(double celsius) {
    return celsius * 1.8 + 32.0;
}

float luce_half_celsius(float celsius) {
    return celsius / 2.0f;
}

luce_half_value luce_adjust_half(luce_half_value value, luce_half_value delta) {
    return value + delta;
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

luce_temperature_range luce_shift_range(luce_temperature_range value, double delta) {
    value.minimum += delta;
    value.maximum += delta;
    return value;
}

luce_temperature_reading luce_shift_reading(luce_temperature_reading value, luce_degrees delta) {
    value.range.minimum += delta;
    value.range.maximum += delta;
    value.current += delta;
    value.fraction += (_Float16)0.5;
    return value;
}

luce_temperature_sensor *luce_temperature_sensor_open(luce_degrees value) {
    luce_sensor.value = value;
    return &luce_sensor;
}

luce_temperature_sensor *luce_temperature_sensor_find(luce_degrees value) {
    if (value < 0) {
        return 0;
    }
    return luce_temperature_sensor_open(value);
}

luce_degrees luce_temperature_sensor_value(const luce_temperature_sensor *sensor) {
    return sensor->value;
}

luce_temperature_sensor *luce_temperature_sensor_echo(luce_temperature_sensor *sensor) {
    return sensor;
}
