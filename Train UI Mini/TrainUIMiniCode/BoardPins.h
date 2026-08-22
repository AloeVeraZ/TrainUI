#pragma once

#include <Arduino.h>

namespace BoardPins {
constexpr uint8_t EPD_POWER = 7;
constexpr uint8_t EPD_BUSY = 9;
constexpr uint8_t EPD_RESET = 10;
constexpr uint8_t EPD_MOSI = 11;
constexpr uint8_t EPD_SCK = 12;
constexpr uint8_t EPD_DC = 13;
constexpr uint8_t EPD_CS = 14;
constexpr uint8_t POWER_LED = 19;

constexpr uint8_t BUTTON_BACK = 1;
constexpr uint8_t BUTTON_MENU = 2;
constexpr uint8_t DIAL_DOWN = 4;
constexpr uint8_t DIAL_PRESS = 5;
constexpr uint8_t DIAL_UP = 6;
}  // namespace BoardPins

