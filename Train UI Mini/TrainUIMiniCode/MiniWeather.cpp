#include "MiniWeather.h"

#include <HTTPClient.h>
#include <WiFiClientSecure.h>

namespace {
constexpr char URL[] =
  "https://api.open-meteo.com/v1/forecast?latitude=40.5749&longitude=-73.9859"
  "&current=temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m"
  "&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=America%2FNew_York";

bool numberAfter(const String &body, const char *key, int searchFrom, float &value) {
  const String needle = String('"') + key + "\":";
  int start = body.indexOf(needle,searchFrom); if (start < 0) return false;
  start += needle.length();
  while (start < static_cast<int>(body.length()) && isspace(body[start])) ++start;
  int end=start;
  while (end < static_cast<int>(body.length()) &&
         (isDigit(body[end]) || body[end]=='-' || body[end]=='+' || body[end]=='.')) ++end;
  if (end == start) return false;
  value = body.substring(start,end).toFloat(); return true;
}
}

String MiniWeather::conditionName(int code) {
  if (code == 0) return "CLEAR";
  if (code <= 2) return "MOSTLY CLEAR";
  if (code == 3) return "OVERCAST";
  if (code == 45 || code == 48) return "FOG";
  if (code >= 51 && code <= 57) return "DRIZZLE";
  if ((code >= 61 && code <= 67) || (code >= 80 && code <= 82)) return "RAIN";
  if ((code >= 71 && code <= 77) || (code >= 85 && code <= 86)) return "SNOW";
  if (code >= 95) return "THUNDER";
  return "WEATHER";
}

bool MiniWeather::fetch(MiniWeatherSnapshot &result, String &error) {
  error="";
  WiFiClientSecure client; client.setInsecure();
  HTTPClient http; http.setTimeout(12000);
  if (!http.begin(client,URL)) { error="WEATHER CONNECTION FAILED"; return false; }
  const int code=http.GET();
  if (code != HTTP_CODE_OK) { error="WEATHER HTTP " + String(code); http.end(); return false; }
  const String body=http.getString(); http.end();
  const int currentStart=body.indexOf("\"current\":{");
  if (currentStart < 0) { error="WEATHER DATA INVALID"; return false; }
  float temperature,wind,humidity,weatherCode;
  if (!numberAfter(body,"temperature_2m",currentStart,temperature) ||
      !numberAfter(body,"wind_speed_10m",currentStart,wind) ||
      !numberAfter(body,"relative_humidity_2m",currentStart,humidity) ||
      !numberAfter(body,"weather_code",currentStart,weatherCode)) {
    error="WEATHER DATA INVALID"; return false;
  }
  result.valid=true; result.temperature=round(temperature); result.wind=round(wind);
  result.humidity=round(humidity); result.code=round(weatherCode);
  result.condition=conditionName(result.code); return true;
}
