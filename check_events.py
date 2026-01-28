#!/usr/bin/env python3
import json
from tools.calendar_ops import list_events_json

events = json.loads(list_events_json())
print(json.dumps(events, indent=2))
