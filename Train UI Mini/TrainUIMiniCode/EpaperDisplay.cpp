#include "EpaperDisplay.h"

#include <SPI.h>

#include "BoardPins.h"

namespace {
SPIClass &epdSpi = SPI;
constexpr uint8_t SPACE[5] = {0,0,0,0,0};
constexpr uint8_t UNKNOWN[5] = {0x02,0x01,0x51,0x09,0x06};
constexpr uint8_t GLYPHS[][5] = {
  {0x3E,0x51,0x49,0x45,0x3E},{0x00,0x42,0x7F,0x40,0x00},
  {0x42,0x61,0x51,0x49,0x46},{0x21,0x41,0x45,0x4B,0x31},
  {0x18,0x14,0x12,0x7F,0x10},{0x27,0x45,0x45,0x45,0x39},
  {0x3C,0x4A,0x49,0x49,0x30},{0x01,0x71,0x09,0x05,0x03},
  {0x36,0x49,0x49,0x49,0x36},{0x06,0x49,0x49,0x29,0x1E},
  {0x7E,0x11,0x11,0x11,0x7E},{0x7F,0x49,0x49,0x49,0x36},
  {0x3E,0x41,0x41,0x41,0x22},{0x7F,0x41,0x41,0x22,0x1C},
  {0x7F,0x49,0x49,0x49,0x41},{0x7F,0x09,0x09,0x09,0x01},
  {0x3E,0x41,0x49,0x49,0x7A},{0x7F,0x08,0x08,0x08,0x7F},
  {0x00,0x41,0x7F,0x41,0x00},{0x20,0x40,0x41,0x3F,0x01},
  {0x7F,0x08,0x14,0x22,0x41},{0x7F,0x40,0x40,0x40,0x40},
  {0x7F,0x02,0x0C,0x02,0x7F},{0x7F,0x04,0x08,0x10,0x7F},
  {0x3E,0x41,0x41,0x41,0x3E},{0x7F,0x09,0x09,0x09,0x06},
  {0x3E,0x41,0x51,0x21,0x5E},{0x7F,0x09,0x19,0x29,0x46},
  {0x46,0x49,0x49,0x49,0x31},{0x01,0x01,0x7F,0x01,0x01},
  {0x3F,0x40,0x40,0x40,0x3F},{0x1F,0x20,0x40,0x20,0x1F},
  {0x3F,0x40,0x38,0x40,0x3F},{0x63,0x14,0x08,0x14,0x63},
  {0x07,0x08,0x70,0x08,0x07},{0x61,0x51,0x49,0x45,0x43}
};
constexpr uint8_t DASH[5] = {0x08,0x08,0x08,0x08,0x08};
constexpr uint8_t DOT[5] = {0,0x60,0x60,0,0};
constexpr uint8_t COLON[5] = {0,0x36,0x36,0,0};
constexpr uint8_t SLASH[5] = {0x20,0x10,0x08,0x04,0x02};
constexpr uint8_t EXCLAMATION[5] = {0,0,0x5F,0,0};
constexpr uint8_t PLUS[5] = {0x08,0x08,0x3E,0x08,0x08};
constexpr uint8_t PERCENT[5] = {0x63,0x13,0x08,0x64,0x63};
}

void EpaperDisplay::begin() {
  pinMode(BoardPins::EPD_POWER, OUTPUT);
  pinMode(BoardPins::EPD_RESET, OUTPUT);
  pinMode(BoardPins::EPD_DC, OUTPUT);
  pinMode(BoardPins::EPD_CS, OUTPUT);
  pinMode(BoardPins::EPD_BUSY, INPUT);
  digitalWrite(BoardPins::EPD_POWER, HIGH);
  digitalWrite(BoardPins::EPD_CS, HIGH);
  epdSpi.begin(BoardPins::EPD_SCK, -1, BoardPins::EPD_MOSI, BoardPins::EPD_CS);
  clear();
}

void EpaperDisplay::command(uint8_t value) {
  epdSpi.beginTransaction(SPISettings(4000000, MSBFIRST, SPI_MODE0));
  digitalWrite(BoardPins::EPD_DC, LOW); digitalWrite(BoardPins::EPD_CS, LOW);
  epdSpi.transfer(value);
  digitalWrite(BoardPins::EPD_CS, HIGH); epdSpi.endTransaction();
}

void EpaperDisplay::data(uint8_t value) {
  epdSpi.beginTransaction(SPISettings(4000000, MSBFIRST, SPI_MODE0));
  digitalWrite(BoardPins::EPD_DC, HIGH); digitalWrite(BoardPins::EPD_CS, LOW);
  epdSpi.transfer(value);
  digitalWrite(BoardPins::EPD_CS, HIGH); epdSpi.endTransaction();
}

void EpaperDisplay::reset() {
  delay(100); digitalWrite(BoardPins::EPD_RESET, HIGH); delay(10);
  digitalWrite(BoardPins::EPD_RESET, LOW); delay(10);
  digitalWrite(BoardPins::EPD_RESET, HIGH); delay(10);
}

bool EpaperDisplay::waitUntilReady(uint32_t timeoutMs) {
  const uint32_t started = millis();
  while (digitalRead(BoardPins::EPD_BUSY) == HIGH) {
    if (millis() - started >= timeoutMs) return false;
    delay(1);
  }
  return true;
}

bool EpaperDisplay::initializeFull() {
  digitalWrite(BoardPins::EPD_POWER, HIGH); delay(100); reset();
  if (!waitUntilReady()) return false;
  command(0x12); if (!waitUntilReady()) return false;
  command(0x01); data(0xF9); data(0x00); data(0x00);
  command(0x11); data(0x03);
  command(0x44); data(0x00); data(0x0F);
  command(0x45); data(0x00); data(0x00); data(0xF9); data(0x00);
  command(0x3C); data(0x01);
  command(0x18); data(0x80);
  command(0x4E); data(0x00);
  command(0x4F); data(0x00); data(0x00);
  return waitUntilReady();
}

bool EpaperDisplay::initializeFast() {
  digitalWrite(BoardPins::EPD_POWER, HIGH); delay(20);
  digitalWrite(BoardPins::EPD_RESET, LOW); delay(10);
  digitalWrite(BoardPins::EPD_RESET, HIGH); delay(10);
  command(0x12); if (!waitUntilReady()) return false;
  command(0x18); data(0x80);
  command(0x22); data(0xB1); command(0x20); if (!waitUntilReady()) return false;
  command(0x1A); data(0x64); data(0x00);
  command(0x22); data(0x91); command(0x20);
  return waitUntilReady();
}

void EpaperDisplay::clear(bool black) { memset(buffer_, black ? 0xFF : 0x00, sizeof(buffer_)); }

void EpaperDisplay::pixel(int x, int y, bool black) {
  if (x < 0 || x >= WIDTH || y < 0 || y >= HEIGHT) return;
  const int rawX = y, rawY = WIDTH - x - 1;
  const size_t address = rawX / 8 + rawY * (RAW_HEIGHT / 8);
  const uint8_t mask = 0x80 >> (rawX % 8);
  if (black) buffer_[address] |= mask; else buffer_[address] &= ~mask;
}

void EpaperDisplay::line(int x0, int y0, int x1, int y1, bool black) {
  const int dx = abs(x1-x0), sx = x0 < x1 ? 1 : -1;
  const int dy = -abs(y1-y0), sy = y0 < y1 ? 1 : -1;
  int error = dx + dy;
  while (true) {
    pixel(x0,y0,black); if (x0 == x1 && y0 == y1) break;
    const int twice = 2*error;
    if (twice >= dy) { error += dy; x0 += sx; }
    if (twice <= dx) { error += dx; y0 += sy; }
  }
}

void EpaperDisplay::rect(int x, int y, int width, int height, bool black) {
  line(x,y,x+width-1,y,black); line(x,y,x,y+height-1,black);
  line(x+width-1,y,x+width-1,y+height-1,black);
  line(x,y+height-1,x+width-1,y+height-1,black);
}

void EpaperDisplay::fillRect(int x, int y, int width, int height, bool black) {
  for (int row=y; row<y+height; ++row) line(x,row,x+width-1,row,black);
}

void EpaperDisplay::circle(int cx, int cy, int r, bool black) {
  int x=r, y=0, error=0;
  while (x >= y) {
    pixel(cx+x,cy+y,black); pixel(cx+y,cy+x,black); pixel(cx-y,cy+x,black); pixel(cx-x,cy+y,black);
    pixel(cx-x,cy-y,black); pixel(cx-y,cy-x,black); pixel(cx+y,cy-x,black); pixel(cx+x,cy-y,black);
    if (error <= 0) { ++y; error += 2*y+1; }
    if (error > 0) { --x; error -= 2*x+1; }
  }
}

void EpaperDisplay::fillCircle(int cx, int cy, int r, bool black) {
  for (int y=-r; y<=r; ++y) {
    const int half = static_cast<int>(sqrt(static_cast<float>(r*r-y*y)));
    line(cx-half,cy+y,cx+half,cy+y,black);
  }
}

const uint8_t *EpaperDisplay::glyph(char c) const {
  if (c >= 'a' && c <= 'z') c -= 32;
  if (c >= '0' && c <= '9') return GLYPHS[c-'0'];
  if (c >= 'A' && c <= 'Z') return GLYPHS[10+c-'A'];
  switch (c) {
    case ' ': return SPACE; case '-': return DASH; case '.': return DOT;
    case ':': return COLON; case '/': return SLASH; case '!': return EXCLAMATION;
    case '+': return PLUS; case '%': return PERCENT; default: return UNKNOWN;
  }
}

void EpaperDisplay::text(int x, int y, const String &value, uint8_t scale, bool black) {
  for (size_t index=0; index<value.length(); ++index) {
    const uint8_t *columns = glyph(value[index]);
    for (uint8_t column=0; column<5; ++column)
      for (uint8_t row=0; row<7; ++row)
        if (columns[column] & (1 << row)) fillRect(x+column*scale,y+row*scale,scale,scale,black);
    x += 6*scale;
  }
}

int EpaperDisplay::textWidth(const String &value, uint8_t scale) const { return value.length()*6*scale; }

bool EpaperDisplay::show(bool fast) {
  if (!(fast ? initializeFast() : initializeFull())) return false;
  command(0x3C); data(0x01); command(0x24);
  for (size_t i=0; i<sizeof(buffer_); ++i) data(~buffer_[i]);
  command(0x22); data(fast ? 0xC7 : 0xF4); command(0x20);
  const bool ready = waitUntilReady();
  command(0x10); data(0x01); delay(20);
  return ready;
}

