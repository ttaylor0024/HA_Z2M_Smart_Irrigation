import os, time, json, logging, requests
from paho.mqtt import client as mqtt

logging.basicConfig(level=logging.INFO)
# load add-on options
with open('/data/options.json') as f:
    cfg = json.load(f)

# extract settings
valve_topics          = cfg['valve_topics']
lat, lon              = cfg['latitude'], cfg['longitude']
fc_pct, fc_hours      = cfg['forecast_threshold_pct'], cfg['forecast_window_hours']
rain_mm, rain_hours   = cfg['rain_threshold_mm'], cfg['rain_window_hours']
target_minutes        = cfg['target_water_minutes']

# MQTT connection (host_network: true → use 'mqtt' hostname)
mqtt_broker = os.getenv('MQTT_BROKER', 'mqtt')
mqtt_port   = int(os.getenv('MQTT_PORT', 1883))
client      = mqtt.Client()
client.username_pw_set(os.getenv('MQTT_USERNAME'), os.getenv('MQTT_PASSWORD'))
client.connect(mqtt_broker, mqtt_port)

def fetch_forecast_pct():
    url = f"https://api.weather.gov/points/{lat},{lon}/forecast"
    r = requests.get(url); r.raise_for_status()
    data = r.json()['properties']['periods']
    # look at next N periods covering fc_hours
    pct = sum(p['probabilityOfPrecipitation']['value'] or 0 for p in data[:fc_hours//12+1]) / (fc_hours//12+1)
    return pct

def fetch_past_rain_mm():
    # use the NWS /observations API for hourly precip
    url = f"https://api.weather.gov/points/{lat},{lon}/observations"
    r = requests.get(url); r.raise_for_status()
    obs = r.json()['features']
    # sum up last rain_hours hours
    total = 0.0
    cutoff = time.time() - rain_hours*3600
    for f in obs:
        ts = time.strptime(f['properties']['timestamp'][:-6], "%Y-%m-%dT%H:%M:%S")
        if time.mktime(ts) >= cutoff:
            total += f['properties']['precipitationLastHour'] or 0
    return total

def water_cycle(minutes):
    secs = minutes * 60
    for topic in valve_topics:
        client.publish(f"zigbee2mqtt/{topic}/set", '{"state":"ON"}')
    logging.info("Watering for %d minutes…", minutes)
    time.sleep(secs)
    for topic in valve_topics:
        client.publish(f"zigbee2mqtt/{topic}/set", '{"state":"OFF"}')
    logging.info("Cycle complete.")

def main():
    try:
        fc = fetch_forecast_pct()
        logging.info("Forecast chance: %s%%", fc)
        if fc >= fc_pct:
            logging.info("Skipping: forecast >= %s%%", fc_pct)
            return

        past = fetch_past_rain_mm()
        logging.info("Past rain: %s mm", past)
        if past >= rain_mm:
            logging.info("Skipping: past rain >= %s mm", rain_mm)
            return

        # only water the remainder
        remain = target_minutes * (1 - past / target_minutes)
        minutes = max(1, round(remain))
        water_cycle(minutes)

    except Exception as e:
        logging.exception("Error in irrigation cycle: %s", e)

if __name__ == "__main__":
    main()
