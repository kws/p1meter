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
        
async def stream_data():
    last_gas_reading: GasReading | None = None
    async with mqtt_publisher() as send_stream:
        async for raw_telegram in mqtt_subscriber():
            parsed_telegram = telegram_to_dict(raw_telegram)
            electricity_reading, gas_reading = to_readings(parsed_telegram)

            elec_json = json.dumps(electricity_reading, cls=ValueJSONEncoder)
            gas_json = json.dumps(gas_reading, cls=ValueJSONEncoder)
    

            await send_stream.send(MQTTMessage(topic="dsmr/reading/electricity", value=elec_json))
            if gas_reading != last_gas_reading:
                await send_stream.send(MQTTMessage(topic="dsmr/reading/gas", value=gas_json))
            last_gas_reading = gas_reading
    

if __name__ == "__main__":
    anyio.run(stream_data)
