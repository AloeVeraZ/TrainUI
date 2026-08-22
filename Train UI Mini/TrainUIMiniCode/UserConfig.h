#pragma once

namespace UserConfig {
// Optional: enter Wi-Fi here, or leave blank and use the setup webpage.
constexpr char WIFI_SSID[] = "";
constexpr char WIFI_PASSWORD[] = "";

// Live mode is the normal startup. When live data is unavailable, the screen
// stays useful with clearly marked offline sample arrivals.
constexpr bool START_IN_OFFLINE_DEMO = false;
}  // namespace UserConfig

