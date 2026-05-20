"""Mock device data for legacy controllers (devType 11 and 18)."""

LEGACY_11_DEVICE = {
    "devCode": "C58ZA",
    "devName": "69 Pro Controller",
    "devType": 11,
    "devId": 11001,
    "online": True,
    "newFrameworkDevice": False,
    "deviceInfo": {
        "temperature": 2400,
        "temperatureF": 7520,
        "humidity": 6000,
        "vpdnums": 130,
        "ports": [
            {"port": 1, "portName": "Intake Fan", "speak": 5, "portsLoad": 1},
            {"port": 2, "portName": "Exhaust Fan", "speak": 7, "portsLoad": 1},
            {"port": 3, "portName": "Humidifier", "speak": 0, "portsLoad": 0},
            {"port": 4, "portName": "Heater", "speak": 0, "portsLoad": 0},
        ],
    },
}

LEGACY_18_DEVICE = {
    "devCode": "E69XB",
    "devName": "69 Pro+ Controller",
    "devType": 18,
    "devId": 18001,
    "online": True,
    "newFrameworkDevice": False,
    "deviceInfo": {
        "temperature": 2350,
        "temperatureF": 7430,
        "humidity": 5800,
        "vpdnums": 140,
        "ports": [
            {"port": 1, "portName": "Fan 1", "speak": 6, "portsLoad": 1},
            {"port": 2, "portName": "Fan 2", "speak": 4, "portsLoad": 1},
        ],
    },
}

LEGACY_HISTORY_RECORD = {
    "createTime": 1714000000,
    "temperature": 2400,
    "fTemperature": 7520,
    "humidity": 6000,
    "vpdNums": 130,
    "portSpead": (7 << 4) | 5,  # port1=5, port2=7
    "portStatus": 0b11,
    "devPortCount": 4,
}
