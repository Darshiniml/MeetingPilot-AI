import unittest

from app.agent.events.event_bus import EventBus
from app.agent.events.event_dispatcher import EventDispatcher
from app.agent.events.event_types import EventType


class EventBusTests(unittest.TestCase):
    def test_dispatcher_publishes_typed_event_to_ordered_listeners(self):
        bus = EventBus()
        received = []
        bus.subscribe(EventType.MEETING_STARTED, lambda event: received.append(("one", event)))
        bus.subscribe(EventType.MEETING_STARTED, lambda event: received.append(("two", event)))

        event = EventDispatcher(bus).dispatch(EventType.MEETING_STARTED, user_id=7, meeting_id=9)

        self.assertEqual([name for name, _ in received], ["one", "two"])
        self.assertEqual(received[0][1].event_id, event.event_id)
        self.assertIsNotNone(event.timestamp)
