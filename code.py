import os
import time
import board
import busio
import adafruit_ina219
import adafruit_ssd1306
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import adafruit_requests as requests
import wifi
import socketpool
import adafruit_io.adafruit_io as IO
import microcontroller
from digitalio import DigitalInOut

# Load settings
wifi_ssid = os.getenv('CIRCUITPY_WIFI_SSID')
wifi_pass = os.getenv('CIRCUITPY_WIFI_PASSWORD')
io_user = os.getenv('ADAFRUIT_IO_USERNAME')
io_key = os.getenv('ADAFRUIT_IO_KEY')

# Initialize I2C and sensors
i2c = busio.I2C(board.GP5, board.GP4)
ina219 = adafruit_ina219.INA219(i2c)

# Initialize OLED
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)

# Connect to WiFi
wifi.radio.connect(wifi_ssid, wifi_pass)
pool = socketpool.SocketPool(wifi.radio)
requests.set_socket(pool)

# MQTT setup
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    username=io_user,
    password=io_key,
)

# Adafruit IO setup
aio = IO.AdafruitIO(mqtt_client, io_user)
aio.subscribe("sameureka/feeds/pico-power.ina219-current")
aio.subscribe("sameureka/feeds/pico-power.ina219-voltage")

# Initialize data variables
current_uA = 0
voltage = 0

# Functional style functions
def read_ina219():
    global current_uA, voltage
    current_uA = ina219.current
    voltage = ina219.bus_voltage + ina219.shunt_voltage / 1000
    return current_uA, voltage

def display_oled(current, voltage):
    oled.fill(0)
    oled.text(f"Current: {current} uA", 0, 0)
    oled.text(f"Voltage: {voltage} V", 0, 10)
    oled.show()

def send_mqtt(current, voltage):
    aio.publish("current", current)
    aio.publish("voltage", voltage)

def web_server():
    while True:
        server = pool.socket()
        server.bind(("", 80))
        server.listen(1)
        client, addr = server.accept()
        print(f"Connection from {addr}")
        client.send("HTTP/1.1 200 OK\n")
        client.send("Content-Type: text/html\n")
        client.send("Connection: close\n\n")
        client.send(f"<html><body><h1>Current: {current_uA} uA</h1><h1>Voltage: {voltage} V</h1></body></html>\n")
        client.close()

def main_loop():
    while True:
        current, voltage = read_ina219()
        display_oled(current, voltage)
        send_mqtt(current, voltage)
        time.sleep(5)

# Start web server
web_server_task = microcontroller.Task(target=web_server, daemon=True)
web_server_task.start()

# Start main loop
main_loop()
