#include "MtaClient.h"

#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <esp_heap_caps.h>
#include <esp32-hal-psram.h>

namespace {
constexpr char ALERT_URL[] =
    "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fall-alerts";
constexpr size_t FALLBACK_DOWNLOAD_CAPACITY = 4U * 1024U * 1024U;
constexpr size_t MAX_DOWNLOAD_CAPACITY = 6U * 1024U * 1024U;

class MemoryStream : public Stream {
 public:
  explicit MemoryStream(size_t capacity) : capacity_(capacity) {
    data_ = static_cast<uint8_t *>(psramFound()
        ? heap_caps_malloc(capacity_, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT)
        : malloc(capacity_));
  }
  ~MemoryStream() override { free(data_); }
  bool good() const { return data_ != nullptr && !overflow_; }
  const uint8_t *data() const { return data_; }
  size_t size() const { return length_; }
  size_t write(uint8_t value) override { return write(&value, 1); }
  size_t write(const uint8_t *buffer, size_t size) override {
    if (!data_ || length_ + size > capacity_) { overflow_ = true; return 0; }
    memcpy(data_ + length_, buffer, size); length_ += size; return size;
  }
  int available() override { return 0; }
  int read() override { return -1; }
  int peek() override { return -1; }
  void flush() override {}
 private:
  uint8_t *data_ = nullptr;
  size_t capacity_ = 0;
  size_t length_ = 0;
  bool overflow_ = false;
};

class ProtoReader {
 public:
  ProtoReader(const uint8_t *data, size_t length) : data_(data), length_(length) {}
  bool key(uint32_t &field, uint8_t &wire) {
    uint64_t value; if (!varint(value)) return false;
    field = static_cast<uint32_t>(value >> 3); wire = value & 7; return field != 0;
  }
  bool varint(uint64_t &value) {
    value = 0;
    for (uint8_t shift=0; shift<64 && position_<length_; shift+=7) {
      const uint8_t byte = data_[position_++]; value |= static_cast<uint64_t>(byte & 0x7F) << shift;
      if (!(byte & 0x80)) return true;
    }
    return false;
  }
  bool slice(ProtoReader &child) {
    uint64_t size; if (!varint(size) || size > length_ - position_) return false;
    child = ProtoReader(data_ + position_, static_cast<size_t>(size)); position_ += size; return true;
  }
  bool stringValue(String &value) {
    uint64_t size; if (!varint(size) || size > length_ - position_) return false;
    value = String(reinterpret_cast<const char *>(data_ + position_), static_cast<unsigned int>(size));
    position_ += size; return true;
  }
  bool skip(uint8_t wire) {
    uint64_t value;
    switch (wire) {
      case 0: return varint(value);
      case 1: if (length_ - position_ < 8) return false; position_ += 8; return true;
      case 2: if (!varint(value) || value > length_ - position_) return false; position_ += value; return true;
      case 5: if (length_ - position_ < 4) return false; position_ += 4; return true;
      default: return false;
    }
  }
  bool done() const { return position_ >= length_; }
 private:
  const uint8_t *data_ = nullptr;
  size_t length_ = 0;
  size_t position_ = 0;
};

bool routeMatches(const String &route, const char *aliases) {
  String list = String(',') + aliases + ',';
  return list.indexOf(String(',') + route + ',') >= 0;
}

void insertMinute(int values[3], int minute) {
  minute = max(0, minute);
  for (int i=0; i<3; ++i) if (values[i] == minute) return;
  for (int i=0; i<3; ++i) {
    if (values[i] < 0 || minute < values[i]) {
      for (int j=2; j>i; --j) values[j] = values[j-1];
      values[i] = minute; return;
    }
  }
}

bool download(const char *url, MemoryStream *&output, String &error) {
  output = nullptr;
  WiFiClientSecure client; client.setInsecure();
  HTTPClient http; http.setTimeout(20000); http.useHTTP10(true);
  if (!http.begin(client, url)) { error = "MTA CONNECTION FAILED"; return false; }
  const int code = http.GET();
  if (code != HTTP_CODE_OK) { error = "MTA HTTP " + String(code); http.end(); return false; }
  const int reported = http.getSize();
  const size_t capacity = reported > 0 ? static_cast<size_t>(reported) + 16 : FALLBACK_DOWNLOAD_CAPACITY;
  if (capacity > MAX_DOWNLOAD_CAPACITY) { error = "MTA FEED TOO LARGE"; http.end(); return false; }
  output = new MemoryStream(capacity);
  if (!output || !output->good()) { error = "NOT ENOUGH PSRAM"; delete output; output=nullptr; http.end(); return false; }
  const int written = http.writeToStream(output);
  http.end();
  if (written < 0 || !output->good() || output->size() == 0) {
    error = "MTA DOWNLOAD FAILED"; delete output; output=nullptr; return false;
  }
  return true;
}

void parseTripDescriptor(ProtoReader reader, String &route) {
  while (!reader.done()) {
    uint32_t field; uint8_t wire; if (!reader.key(field,wire)) break;
    if (field == 5 && wire == 2) { if (!reader.stringValue(route)) break; }
    else if (!reader.skip(wire)) break;
  }
}

void parseStopEvent(ProtoReader reader, uint64_t &timestamp) {
  while (!reader.done()) {
    uint32_t field; uint8_t wire; if (!reader.key(field,wire)) break;
    if (field == 2 && wire == 0) { if (!reader.varint(timestamp)) break; }
    else if (!reader.skip(wire)) break;
  }
}

void parseStopUpdate(ProtoReader reader, String &stop, uint64_t &timestamp) {
  uint64_t arrival=0, departure=0;
  while (!reader.done()) {
    uint32_t field; uint8_t wire; if (!reader.key(field,wire)) break;
    if ((field == 2 || field == 3) && wire == 2) {
      ProtoReader event(nullptr,0); if (!reader.slice(event)) break;
      if (field == 2) parseStopEvent(event,arrival); else parseStopEvent(event,departure);
    } else if (field == 4 && wire == 2) {
      if (!reader.stringValue(stop)) break;
    } else if (!reader.skip(wire)) break;
  }
  timestamp = arrival ? arrival : departure;
}

void parseTripUpdate(ProtoReader reader, const char *aliases, const char *northStop,
                     const char *southStop, int north[3], int south[3], uint64_t now) {
  String route;
  uint64_t northTime=0, southTime=0;
  while (!reader.done()) {
    uint32_t field; uint8_t wire; if (!reader.key(field,wire)) break;
    if (field == 1 && wire == 2) {
      ProtoReader trip(nullptr,0); if (!reader.slice(trip)) break; parseTripDescriptor(trip,route);
    } else if (field == 2 && wire == 2) {
      ProtoReader update(nullptr,0); if (!reader.slice(update)) break;
      String stop; uint64_t stamp=0; parseStopUpdate(update,stop,stamp);
      if (stop == northStop) northTime=stamp;
      if (stop == southStop) southTime=stamp;
    } else if (!reader.skip(wire)) break;
  }
  if (!routeMatches(route,aliases)) return;
  if (northTime && northTime + 60 >= now) insertMinute(north, static_cast<int>((northTime-now+30)/60));
  if (southTime && southTime + 60 >= now) insertMinute(south, static_cast<int>((southTime-now+30)/60));
}

uint64_t parseFeedHeader(ProtoReader reader) {
  uint64_t timestamp=0;
  while (!reader.done()) {
    uint32_t field; uint8_t wire; if (!reader.key(field,wire)) break;
    if (field == 3 && wire == 0) { if (!reader.varint(timestamp)) break; }
    else if (!reader.skip(wire)) break;
  }
  return timestamp;
}

void parseFeedEntityForTrip(ProtoReader reader, const char *aliases, const char *northStop,
                            const char *southStop, int north[3], int south[3], uint64_t now) {
  while (!reader.done()) {
    uint32_t field; uint8_t wire; if (!reader.key(field,wire)) break;
    if (field == 3 && wire == 2) {
      ProtoReader update(nullptr,0); if (!reader.slice(update)) break;
      parseTripUpdate(update,aliases,northStop,southStop,north,south,now);
    } else if (!reader.skip(wire)) break;
  }
}

void parseTranslation(ProtoReader reader, String &text) {
  while (!reader.done()) {
    uint32_t field; uint8_t wire; if (!reader.key(field,wire)) break;
    if (field == 1 && wire == 2 && text.isEmpty()) { if (!reader.stringValue(text)) break; }
    else if (!reader.skip(wire)) break;
  }
}

void parseTranslatedString(ProtoReader reader, String &text) {
  while (!reader.done()) {
    uint32_t field; uint8_t wire; if (!reader.key(field,wire)) break;
    if (field == 1 && wire == 2) {
      ProtoReader translation(nullptr,0); if (!reader.slice(translation)) break; parseTranslation(translation,text);
    } else if (!reader.skip(wire)) break;
  }
}

bool parseSelector(ProtoReader reader, const char *aliases, const char *stationId,
                   const char *northStop, const char *southStop) {
  String route, stop;
  while (!reader.done()) {
    uint32_t field; uint8_t wire; if (!reader.key(field,wire)) break;
    if (field == 2 && wire == 2) { if (!reader.stringValue(route)) break; }
    else if (field == 5 && wire == 2) { if (!reader.stringValue(stop)) break; }
    else if (!reader.skip(wire)) break;
  }
  return (!route.isEmpty() && routeMatches(route,aliases)) || stop == stationId || stop == northStop || stop == southStop;
}

bool parseAlert(ProtoReader reader, const char *aliases, const char *stationId,
                const char *northStop, const char *southStop, String &text) {
  bool matched=false;
  while (!reader.done()) {
    uint32_t field; uint8_t wire; if (!reader.key(field,wire)) break;
    if (field == 5 && wire == 2) {
      ProtoReader selector(nullptr,0); if (!reader.slice(selector)) break;
      matched = parseSelector(selector,aliases,stationId,northStop,southStop) || matched;
    } else if (field == 10 && wire == 2) {
      ProtoReader translated(nullptr,0); if (!reader.slice(translated)) break; parseTranslatedString(translated,text);
    } else if (!reader.skip(wire)) break;
  }
  return matched;
}

bool parseEntityForAlert(ProtoReader reader, const char *aliases, const char *stationId,
                         const char *northStop, const char *southStop, String &text) {
  while (!reader.done()) {
    uint32_t field; uint8_t wire; if (!reader.key(field,wire)) break;
    if (field == 4 && wire == 2) {
      ProtoReader alert(nullptr,0); if (!reader.slice(alert)) break;
      return parseAlert(alert,aliases,stationId,northStop,southStop,text);
    }
    if (!reader.skip(wire)) break;
  }
  return false;
}
}  // namespace

bool MtaClient::fetchArrivals(const char *feedUrl, const char *routeAliases,
                              const char *northStop, const char *southStop,
                              ArrivalSnapshot &result) {
  result = ArrivalSnapshot{};
  MemoryStream *downloaded=nullptr;
  if (!download(feedUrl,downloaded,result.error)) return false;
  ProtoReader feed(downloaded->data(),downloaded->size());
  uint64_t feedTimestamp=0;
  time_t systemNow=time(nullptr);
  while (!feed.done()) {
    uint32_t field; uint8_t wire; if (!feed.key(field,wire)) break;
    if (field == 1 && wire == 2) {
      ProtoReader header(nullptr,0); if (!feed.slice(header)) break; feedTimestamp=parseFeedHeader(header);
    } else if (field == 2 && wire == 2) {
      ProtoReader entity(nullptr,0); if (!feed.slice(entity)) break;
      const uint64_t now = systemNow > 1500000000 ? static_cast<uint64_t>(systemNow) : feedTimestamp;
      parseFeedEntityForTrip(entity,routeAliases,northStop,southStop,result.north,result.south,now);
    } else if (!feed.skip(wire)) break;
  }
  delete downloaded;
  result.valid = result.north[0] >= 0 || result.south[0] >= 0;
  if (!result.valid) result.error = "NO UPCOMING TRAINS";
  return result.valid;
}

bool MtaClient::fetchAlert(const char *routeAliases, const char *stationId,
                           const char *northStop, const char *southStop,
                           String &alertText, String &error) {
  alertText=""; error="";
  MemoryStream *downloaded=nullptr;
  if (!download(ALERT_URL,downloaded,error)) return false;
  ProtoReader feed(downloaded->data(),downloaded->size());
  while (!feed.done() && alertText.isEmpty()) {
    uint32_t field; uint8_t wire; if (!feed.key(field,wire)) break;
    if (field == 2 && wire == 2) {
      ProtoReader entity(nullptr,0); if (!feed.slice(entity)) break;
      String candidate;
      if (parseEntityForAlert(entity,routeAliases,stationId,northStop,southStop,candidate)) alertText=candidate;
    } else if (!feed.skip(wire)) break;
  }
  delete downloaded;
  return true;
}

