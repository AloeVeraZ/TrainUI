#pragma once

#include <Arduino.h>

struct MiniWeatherSnapshot {
  bool valid = false;
  int temperature = 0;
  int wind = 0;
  int humidity = 0;
  int code = 0;
  String condition = "--";
};

class MiniWeather {
 public:
  bool fetch(MiniWeatherSnapshot &result, String &error);
  static String conditionName(int code);
};

