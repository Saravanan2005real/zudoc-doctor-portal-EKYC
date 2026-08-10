from threading import Lock
import threading

class MemoryEventBus:
    def __init__(self):
        self.mu = Lock()
        self.handlers = {}

    def subscribe(self, event_type: str, handler):
        with self.mu:
            if event_type not in self.handlers:
                self.handlers[event_type] = []
            self.handlers[event_type].append(handler)
            print(f"[EVENT BUS] Subscribed handler to event '{event_type}'")

    def publish(self, context, event):
        with self.mu:
            handlers = self.handlers.get(event.get_type(), [])

        if not handlers:
            return

        print(f"[EVENT BUS] Publishing Event '{event.get_type()}' for Doctor '{event.get_doctor_id()}'")

        for handler in handlers:
            def run_handler(h):
                try:
                    h(context, event)
                except Exception as e:
                    print(f"[EVENT BUS] Error handling event '{event.get_type()}': {e}")
            
            threading.Thread(target=run_handler, args=(handler,)).start()
