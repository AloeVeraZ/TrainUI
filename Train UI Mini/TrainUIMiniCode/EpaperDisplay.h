#pragma once

#include <Arduino.h>

class EpaperDisplay {
 public:
  static constexpr int WIDTH = 250;
  static constexpr int HEIGHT = 122;

  void begin();
  void clear(bool black = false);
  void pixel(int x, int y, bool black = true);
  void line(int x0, int y0, int x1, int y1, bool black = true);
  void rect(int x, int y, int width, int height, bool black = true);
  void fillRect(int x, int y, int width, int height, bool black = true);
  void circle(int centerX, int centerY, int radius, bool black = true);
  void fillCircle(int centerX, int centerY, int radius, bool black = true);
  void text(int x, int y, const String &value, uint8_t scale = 1, bool black = true);
  int textWidth(const String &value, uint8_t scale = 1) const;
  bool show(bool fast = false);

 private:
  static constexpr int RAW_HEIGHT = 128;
  static constexpr size_t BUFFER_SIZE = WIDTH * RAW_HEIGHT / 8;
  uint8_t buffer_[BUFFER_SIZE]{};

  void command(uint8_t value);
  void data(uint8_t value);
  void reset();
  bool waitUntilReady(uint32_t timeoutMs = 15000);
  void configureRam();
  bool initializeFull();
  bool initializeFast();
  const uint8_t *glyph(char character) const;
};
