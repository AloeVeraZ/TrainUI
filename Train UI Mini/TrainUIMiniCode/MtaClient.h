#pragma once

#include <Arduino.h>

struct ArrivalSnapshot {
  bool valid = false;
  int north[3] = {-1, -1, -1};
  int south[3] = {-1, -1, -1};
  String error;
};

class MtaClient {
 public:
  bool fetchArrivals(const char *feedUrl, const char *routeAliases,
                     const char *northStop, const char *southStop,
                     ArrivalSnapshot &result);
  bool fetchAlert(const char *routeAliases, const char *stationId,
                  const char *northStop, const char *southStop,
                  String &alertText, String &error);
};

