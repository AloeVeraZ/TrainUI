#include <Arduino.h>
#include <Preferences.h>
#include <WebServer.h>
#include <WiFi.h>
#include <time.h>

#include "BoardPins.h"
#include "EpaperDisplay.h"
#include "MiniWeather.h"
#include "MtaClient.h"
#include "SubwayCatalog.h"
#include "UserConfig.h"

namespace {
constexpr uint32_t ARRIVAL_REFRESH_MS = 60UL * 1000UL;
constexpr uint32_t WEATHER_REFRESH_MS = 10UL * 60UL * 1000UL;
constexpr uint32_t ALERT_REFRESH_MS = 5UL * 60UL * 1000UL;
constexpr uint32_t PORTAL_TIMEOUT_MS = 15UL * 60UL * 1000UL;
constexpr char SETUP_SSID[] = "TrainUIMini";
constexpr char SETUP_PASSWORD[] = "TRAINUI1";

EpaperDisplay display;
Preferences preferences;
WebServer server(80);
MtaClient mta;
MiniWeather weatherClient;
ArrivalSnapshot arrivals;
MiniWeatherSnapshot weather;

String wifiSsid, wifiPassword, selectedRouteId, selectedStationId;
String serviceAlert, mtaError, weatherError;
const SubwayCatalog::RouteDef *selectedRoute = nullptr;
const SubwayCatalog::StationDef *selectedStation = nullptr;
bool configured = false;
bool offlineDemo = false;
bool portalRunning = false;
bool hasShownDashboard = false;
uint32_t portalStarted = 0;
uint32_t lastArrivalFetch = 0;
uint32_t lastWeatherFetch = 0;
uint32_t lastAlertFetch = 0;
uint16_t screenRefreshCount = 0;

class Button {
 public:
  explicit Button(uint8_t pin) : pin_(pin) {}
  void begin() { pinMode(pin_,INPUT_PULLUP); stable_=digitalRead(pin_); raw_=stable_; }
  bool pressed() {
    const bool reading=digitalRead(pin_);
    if (reading != raw_) { raw_=reading; changed_=millis(); }
    if (millis()-changed_>35 && reading != stable_) { stable_=reading; return stable_==LOW; }
    return false;
  }
 private:
  uint8_t pin_; bool stable_=HIGH,raw_=HIGH; uint32_t changed_=0;
};

Button menuButton(BoardPins::BUTTON_MENU);
Button backButton(BoardPins::BUTTON_BACK);
Button dialPressButton(BoardPins::DIAL_PRESS);

String htmlEscape(String value) {
  value.replace("&","&amp;"); value.replace("\"","&quot;");
  value.replace("<","&lt;"); value.replace(">","&gt;"); return value;
}

String cleanDisplay(String value, size_t maximum) {
  value.toUpperCase();
  String clean; clean.reserve(value.length());
  bool previousSpace=false;
  for (size_t i=0;i<value.length();++i) {
    char c=value[i];
    if (c < 32 || c > 126) c=' ';
    if (c==' ' && previousSpace) continue;
    clean += c; previousSpace=(c==' ');
  }
  clean.trim();
  if (clean.length()>maximum) clean=clean.substring(0,maximum);
  return clean;
}

String localClock() {
  struct tm info;
  if (getLocalTime(&info,10)) {
    char output[9]; strftime(output,sizeof(output),"%I:%M %p",&info);
    String value(output); if (value[0]=='0') value.remove(0,1); return value;
  }
  return "--:--";
}

String connectionState() {
  if (offlineDemo) return "OFFLINE";
  return WiFi.status()==WL_CONNECTED ? "ONLINE" : "OFFLINE";
}

void loadOfflineDemo() {
  arrivals=ArrivalSnapshot{}; arrivals.valid=true;
  arrivals.north[0]=3; arrivals.north[1]=8; arrivals.north[2]=14;
  arrivals.south[0]=5; arrivals.south[1]=11; arrivals.south[2]=17;
  weather.valid=true; weather.temperature=72; weather.wind=6; weather.humidity=52;
  weather.code=1; weather.condition="MOSTLY CLEAR";
  serviceAlert=""; mtaError="OFFLINE SAMPLE ARRIVALS"; weatherError="";
}

void loadSettings() {
  preferences.begin("trainmini",true);
  configured=preferences.getBool("configured",false);
  wifiSsid=preferences.getString("ssid","");
  wifiPassword=preferences.getString("pass","");
  selectedRouteId=preferences.getString("route","");
  selectedStationId=preferences.getString("station","");
  const bool modeSet=preferences.getBool("modeset",false);
  const bool savedDemo=preferences.getBool("demo",false);
  preferences.end();
  if (wifiSsid.isEmpty() && UserConfig::WIFI_SSID[0]) {
    wifiSsid=UserConfig::WIFI_SSID; wifiPassword=UserConfig::WIFI_PASSWORD;
  }
  offlineDemo=modeSet ? savedDemo : UserConfig::START_IN_OFFLINE_DEMO;
  selectedRoute=SubwayCatalog::findRoute(selectedRouteId);
  selectedStation=selectedRoute ? SubwayCatalog::findStation(*selectedRoute,selectedStationId) : nullptr;
  if (!selectedRoute || !selectedStation) configured=false;
}

void drawBadge(int centerX, int centerY, const String &badge) {
  display.fillCircle(centerX,centerY,10,true);
  const uint8_t scale=badge.length()==1 ? 2 : 1;
  const int x=display.centeredTextX(centerX,badge,scale);
  display.text(x,centerY-(7*scale)/2,badge,scale,false);
}

String minuteText(int minute) {
  if (minute < 0) return "--";
  if (minute == 0) return "DUE";
  return String(minute);
}

void renderDirectionCard(int x, const String &label, const int values[3]) {
  display.rect(x,27,119,55);
  display.text(x+5,31,cleanDisplay(label,17),1);
  display.line(x+4,41,x+114,41);
  const String first=minuteText(values[0]);
  const uint8_t firstScale=first=="DUE" ? 2 : 3;
  display.text(x+6,47,first,firstScale);
  if (first != "DUE") display.text(x+6+display.textWidth(first,firstScale)+3,58,"MIN",1);
  display.text(x+72,47,"NEXT",1);
  display.text(x+72,61,minuteText(values[1])+" / "+minuteText(values[2]),1);
}

void renderSetupScreen() {
  display.clear();
  display.text(5,5,"TRAIN UI MINI",2);
  display.line(5,23,244,23);
  display.text(5,31,"CHOOSE TRAIN + STATION",1);
  display.text(5,47,"WI-FI: TRAINUIMINI",1);
  display.text(5,61,"PASSWORD: TRAINUI1",1);
  display.text(5,75,"OPEN: 192.168.4.1",1);
  display.text(5,94,"SETUP CLOSES IN 15 MIN",1);
  display.text(5,112,"MENU REOPENS SETUP",1);
  display.show(false);
}

void renderDashboard() {
  if (!selectedRoute || !selectedStation) { renderSetupScreen(); return; }
  display.clear();
  drawBadge(14,12,selectedRoute->badge);
  display.text(30,3,cleanDisplay(selectedStation->name,27),1);
  const String state=connectionState();
  display.text(246-display.textWidth(state,1),3,state,1);
  display.text(30,14,cleanDisplay(String(selectedStation->borough)+" / "+selectedRoute->service,24),1);
  const String clock=localClock();
  display.text(246-display.textWidth(clock,1),14,clock,1);
  display.line(4,24,246,24);

  renderDirectionCard(4,selectedStation->northLabel,arrivals.north);
  renderDirectionCard(127,selectedStation->southLabel,arrivals.south);

  display.rect(4,86,242,35);
  const String statusTitle = serviceAlert.isEmpty() ? "GOOD SERVICE" : "SERVICE ALERT";
  display.text(9,90,statusTitle,1);
  String weatherLine=weather.valid ? "TEMP "+String(weather.temperature)+"F" :
                     (weatherError.isEmpty() ? "TEMP --" : "TEMP ERR");
  weatherLine=cleanDisplay(weatherLine,19);
  display.text(241-display.textWidth(weatherLine,1),90,weatherLine,1);
  String statusLine;
  if (!serviceAlert.isEmpty()) statusLine=serviceAlert;
  else if (offlineDemo) statusLine="OFFLINE DEMO / PRESS DIAL FOR LIVE";
  else if (!mtaError.isEmpty()) statusLine=mtaError;
  else statusLine=String(selectedRoute->service)+" IS OPERATING NORMALLY";
  display.text(9,101,cleanDisplay(statusLine,38),1);
  String footer="UPDATED "+localClock()+" / "+state;
  display.text(9,112,cleanDisplay(footer,30),1);
  display.text(241-display.textWidth("ALOE",1),112,"ALOE",1);

  const bool fast=hasShownDashboard && (++screenRefreshCount % 10 != 0);
  display.show(fast); hasShownDashboard=true;
}

String pageStart() {
  return F("<!doctype html><html><head><meta name=viewport content='width=device-width,initial-scale=1'>"
           "<title>Train UI Mini</title><style>body{font:17px system-ui;max-width:650px;margin:28px auto;padding:0 18px;background:#071321;color:#f5f8ff}"
           "h1{font-size:31px;margin-bottom:6px}.muted{color:#9cb0cf}label{display:block;font-weight:700;margin-top:18px}"
           "input,select{box-sizing:border-box;width:100%;font:inherit;padding:12px;border:2px solid #526b91;border-radius:8px;background:#fff;color:#111}"
           ".check{display:flex;gap:10px;align-items:center}.check input{width:auto}button{width:100%;margin-top:24px;background:#fff;color:#071321;border:0;border-radius:8px;padding:14px;font:800 18px system-ui}</style></head><body>");
}

String routeSetupPage() {
  String page=pageStart(); page.reserve(9000);
  page += F("<h1>Train UI Mini</h1><p class=muted>Connect Wi-Fi, choose an NYC train, then choose a station served by it.</p>"
            "<form method=post action=/stations><label>Home Wi-Fi name</label><input name=ssid required value=\"");
  page += htmlEscape(wifiSsid);
  page += F("\"><label>Wi-Fi password</label><input type=password name=pass placeholder='Leave blank to keep saved password'>"
            "<label>Train</label><select name=route required><option value=''>Choose a train...</option>");
  for (size_t i=0;i<SubwayCatalog::ROUTE_COUNT;++i) {
    const auto &route=SubwayCatalog::ROUTES[i];
    page += "<option value='"+String(route.id)+"'";
    if (selectedRouteId==route.id) page += " selected";
    page += ">"+htmlEscape(String(route.service))+"</option>";
  }
  page += F("</select><label class=check><input type=checkbox name=demo value=1>Start with offline sample arrivals</label>"
            "<button type=submit>Next: choose station</button></form></body></html>");
  return page;
}

String stationSetupPage(const SubwayCatalog::RouteDef &route) {
  String page=pageStart(); page.reserve(14000);
  page += "<h1>Choose a station</h1><p class=muted>Showing stations served by the "+htmlEscape(String(route.service))+".</p>";
  page += "<form method=post action=/save><input type=hidden name=ssid value=\""+htmlEscape(server.arg("ssid"))+"\">";
  page += "<input type=hidden name=pass value=\""+htmlEscape(server.arg("pass"))+"\">";
  page += "<input type=hidden name=route value=\""+String(route.id)+"\">";
  if (server.hasArg("demo")) page += "<input type=hidden name=demo value=1>";
  page += "<label>Station</label><select name=station required><option value=''>Choose a station...</option>";
  for (uint16_t i=0;i<route.stationCount;++i) {
    const auto &station=SubwayCatalog::STATIONS[route.stationStart+i];
    page += "<option value='"+String(station.id)+"'";
    if (selectedRouteId==route.id && selectedStationId==station.id) page += " selected";
    page += ">"+htmlEscape(String(station.name))+" ("+station.borough+")</option>";
  }
  page += F("</select><button type=submit>Save and start display</button></form>"
            "<form method=get action='/'><button type=submit>Back</button></form></body></html>");
  return page;
}

void stopPortal() {
  if (!portalRunning) return;
  server.stop(); WiFi.softAPdisconnect(true); portalRunning=false;
  if (WiFi.status()==WL_CONNECTED) WiFi.mode(WIFI_STA);
}

void startPortal() {
  WiFi.mode(WIFI_AP_STA); WiFi.softAP(SETUP_SSID,SETUP_PASSWORD);
  server.on("/",HTTP_GET,[]{ server.send(200,"text/html",routeSetupPage()); });
  server.on("/stations",HTTP_POST,[]{
    const auto *route=SubwayCatalog::findRoute(server.arg("route"));
    if (!route) { server.send(400,"text/plain","Choose a valid train, then go back."); return; }
    server.send(200,"text/html",stationSetupPage(*route));
  });
  server.on("/save",HTTP_POST,[]{
    const auto *route=SubwayCatalog::findRoute(server.arg("route"));
    const auto *station=route ? SubwayCatalog::findStation(*route,server.arg("station")) : nullptr;
    const String newSsid=server.arg("ssid");
    if (!route || !station || (newSsid.isEmpty() && UserConfig::WIFI_SSID[0]=='\0')) {
      server.send(400,"text/plain","Wi-Fi, train, or station is invalid. Go back and try again."); return;
    }
    preferences.begin("trainmini",false);
    preferences.putBool("configured",true); preferences.putString("ssid",newSsid);
    if (!server.arg("pass").isEmpty()) preferences.putString("pass",server.arg("pass"));
    preferences.putString("route",route->id); preferences.putString("station",station->id);
    preferences.putBool("demo",server.hasArg("demo")); preferences.putBool("modeset",true);
    preferences.end();
    server.send(200,"text/html","<h2>Saved.</h2><p>Train UI Mini is restarting.</p>");
    delay(900); ESP.restart();
  });
  server.onNotFound([]{server.sendHeader("Location","/",true); server.send(302,"text/plain","");});
  server.begin(); portalRunning=true; portalStarted=millis(); renderSetupScreen();
}

bool connectWifi() {
  if (wifiSsid.isEmpty()) return false;
  WiFi.mode(WIFI_STA); WiFi.begin(wifiSsid.c_str(),wifiPassword.c_str());
  const uint32_t started=millis();
  while (WiFi.status()!=WL_CONNECTED && millis()-started<18000) delay(150);
  if (WiFi.status()==WL_CONNECTED) {
    configTzTime("EST5EDT,M3.2.0/2,M11.1.0/2","pool.ntp.org","time.nist.gov"); return true;
  }
  return false;
}

void updateLive(bool forceAll=false) {
  if (offlineDemo) { loadOfflineDemo(); renderDashboard(); return; }
  if (WiFi.status()!=WL_CONNECTED && !connectWifi()) {
    mtaError="WI-FI UNAVAILABLE"; loadOfflineDemo(); offlineDemo=true; renderDashboard(); return;
  }
  const uint32_t now=millis();
  if (forceAll || now-lastArrivalFetch>=ARRIVAL_REFRESH_MS) {
    ArrivalSnapshot fresh;
    if (mta.fetchArrivals(selectedRoute->feedUrl,selectedRoute->aliases,
                          selectedStation->northStop,selectedStation->southStop,fresh)) arrivals=fresh;
    else mtaError=fresh.error;
    if (fresh.valid) mtaError="";
    lastArrivalFetch=now;
  }
  const uint32_t weatherInterval=(weather.valid && weatherError.isEmpty()) ?
                                 WEATHER_REFRESH_MS : ARRIVAL_REFRESH_MS;
  if (forceAll || now-lastWeatherFetch>=weatherInterval) {
    MiniWeatherSnapshot fresh;
    if (weatherClient.fetch(fresh,weatherError)) weather=fresh;
    lastWeatherFetch=now;
  }
  if (forceAll || now-lastAlertFetch>=ALERT_REFRESH_MS) {
    String freshAlert,error;
    if (mta.fetchAlert(selectedRoute->aliases,selectedStation->id,
                       selectedStation->northStop,selectedStation->southStop,freshAlert,error)) serviceAlert=freshAlert;
    lastAlertFetch=now;
  }
  renderDashboard();
}
}  // namespace

void setup() {
  Serial.begin(115200);
  pinMode(BoardPins::POWER_LED,OUTPUT); digitalWrite(BoardPins::POWER_LED,HIGH);
  display.begin(); menuButton.begin(); backButton.begin(); dialPressButton.begin();
  loadSettings();
  if (!configured) startPortal();
  else if (offlineDemo) { loadOfflineDemo(); renderDashboard(); }
  else updateLive(true);
}

void loop() {
  if (portalRunning) {
    server.handleClient();
    if (millis()-portalStarted>=PORTAL_TIMEOUT_MS) { stopPortal(); renderDashboard(); }
  } else {
    if (menuButton.pressed()) startPortal();
    if (dialPressButton.pressed()) {
      offlineDemo=!offlineDemo;
      preferences.begin("trainmini",false); preferences.putBool("demo",offlineDemo);
      preferences.putBool("modeset",true); preferences.end();
      if (offlineDemo) { loadOfflineDemo(); renderDashboard(); }
      else updateLive(true);
    }
    if (backButton.pressed() && !offlineDemo) updateLive(true);
    if (!offlineDemo && millis()-lastArrivalFetch>=ARRIVAL_REFRESH_MS) updateLive(false);
  }
  delay(5);
}
