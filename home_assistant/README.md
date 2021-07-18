To successfully use the MQTT values provided by the Parking Assistant in Home Assistant, you must manully create the sensors listed above under a sensor: section of your configuration.yaml, or in a separate sensors.yaml file, included in the configuration.yaml.

If you changed the MQTT topics in the Python file, you must also change the sensor listed here to use the same topics.
