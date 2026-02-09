from p1_decoder._mqtt import mqtt_publisher, mqtt_subscriber, MQTTMessage
from p1_decoder._pipeline import GasReading, Value, telegram_to_dict, to_readings
import anyio
import json


class ValueJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Value):
            return obj.value
        elif hasattr(obj, "to_dict"):
            return obj.to_dict()
        return super().default(obj)


def _get_gas_delta(old_reading: GasReading, new_reading: GasReading) -> float:
    delta_t = new_reading.timestamp - old_reading.timestamp # Timestamps are in seconds since epoch
    if delta_t < 1:
        return None
    delta_m3 = float(new_reading.reading_m3.value) - float(old_reading.reading_m3.value)
    return delta_m3 / (delta_t / 3600)
        
async def stream_data():
    last_gas_reading: GasReading | None = None
    async with mqtt_publisher() as send_stream:
        async for raw_telegram in mqtt_subscriber():
            parsed_telegram = telegram_to_dict(raw_telegram)
            electricity_reading, gas_reading = to_readings(parsed_telegram)

            elec_json = json.dumps(electricity_reading, cls=ValueJSONEncoder)

            await send_stream.send(MQTTMessage(topic="dsmr/reading/electricity", value=elec_json))

            if gas_reading != last_gas_reading:
                gas_dict = gas_reading.to_dict()
                if last_gas_reading is not None:
                    delta = _get_gas_delta(last_gas_reading, gas_reading)
                    if delta is not None:
                        gas_dict["m3_per_hour"] = delta
                gas_json = json.dumps(gas_dict, cls=ValueJSONEncoder)
                await send_stream.send(MQTTMessage(topic="dsmr/reading/gas", value=gas_json))

            last_gas_reading = gas_reading
    



if __name__ == "__main__":
    anyio.run(stream_data)
