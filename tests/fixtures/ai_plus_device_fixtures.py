"""Mock device data for AI+ controllers (devType 20+)."""

AI_PLUS_DEVICE = {
    "devCode": "D89XA",
    "devName": "89 AI+ Controller",
    "devType": 20,
    "devId": 20001,
    "online": True,
    "newFrameworkDevice": True,
    "deviceInfo": {
        "temperature": 2350,
        "temperatureF": 7430,
        "humidity": 5500,
        "vpdnums": 145,
        "ports": [
            {"port": 1, "portName": "Fan Port", "speak": 5, "portsLoad": 1},
            {"port": 2, "portName": "Light", "speak": 0, "portsLoad": 0},
        ],
    },
}

AI_PLUS_HISTORY_RECORD = {
    "createTime": 1714000000,
    "temperature": 2350,
    "fTemperature": 7430,
    "humidity": 5500,
    "vpdNums": 145,
    "portSpead": 5,
    "portStatus": 1,
    "devPortCount": 2,
}
