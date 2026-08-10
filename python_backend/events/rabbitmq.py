import json
import pika
from events.bus import MemoryEventBus

class RabbitMQEventBus:
    def __init__(self, amqp_url: str):
        self.amqp_url = amqp_url
        self.memory_bus = MemoryEventBus()

    def subscribe(self, event_type: str, handler):
        self.memory_bus.subscribe(event_type, handler)

    def publish(self, context, event):
        try:
            event_bytes = json.dumps(event.__dict__, default=str).encode('utf-8')
            print(f"[RABBITMQ EVENT BUS] Serialized event payload ({len(event_bytes)} bytes) for channel '{event.get_type()}'")
            # In a real implementation, we would use pika to publish
            # connection = pika.BlockingConnection(pika.URLParameters(self.amqp_url))
            # channel = connection.channel()
            # channel.basic_publish(exchange='', routing_key=event.get_type(), body=event_bytes)
            # connection.close()
        except Exception:
            pass
        self.memory_bus.publish(context, event)
