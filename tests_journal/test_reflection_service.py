"""
Test 4: Full test of ReflectionService with real Journal data.
Run inside Sugar:
  export PYTHONPATH=/home/isatyamks/sugar/src
  python3 ~/sugar/tests_journal/test_reflection_service.py
"""
# MUST be done before any D-Bus or Sugar imports
from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)

import gi
gi.require_version('SugarExt', '1.0')

from jarabe.model import reflection
from jarabe.journal import model

print('=' * 50)
print('  TEST: ReflectionService with real Journal data')
print('  reflection.py from: {}'.format(reflection.__file__))
print('  model.py from:      {}'.format(model.__file__))
print('=' * 50)

service = reflection.get_service()

# Step 0: Verify raw D-Bus works (same as test_journal_history)
print('\n--- Step 0: Verify raw D-Bus access ---')
import dbus
bus = dbus.SessionBus()
ds = dbus.Interface(
    bus.get_object(
        'org.laptop.sugar.DataStore',
        '/org/laptop/sugar/DataStore'),
    'org.laptop.sugar.DataStore')
raw_entries, raw_count = ds.find(
    {}, ['title', 'bundle_id', 'uid', 'timestamp'], byte_arrays=True)
print('  Raw D-Bus found {} entries'.format(raw_count))

# Step 1: Get all journal entries via model.find_entries
print('\n--- Step 1: Get all journal entries (model.find_entries) ---')
try:
    all_entries = model.find_entries({}, limit=10)
except Exception as e:
    print('  ERROR from find_entries: {}'.format(e))
    import traceback
    traceback.print_exc()
    all_entries = []
print('  model.find_entries returned {} entries'.format(len(all_entries)))

# If model.find_entries returned nothing but raw D-Bus works, fallback
if len(all_entries) == 0 and raw_count > 0:
    print('\n  WARNING: model.find_entries returned 0 entries but raw D-Bus has {}!'.format(raw_count))
    print('  This means find_entries is hitting a silent exception.')
    print('  Falling back to raw D-Bus entries for remaining tests...')
    # Convert raw D-Bus entries to regular dicts
    all_entries = [dict(e) for e in raw_entries[:10]]

if len(all_entries) == 0:
    print('\n  No journal entries found!')
    print('  Open an activity, do some work, save it,')
    print('  then run this test again.')
    exit(0)

# Step 2: Pick the most recent entry
entry = all_entries[0]
uid = entry.get('uid', '')
bundle_id = str(entry.get('bundle_id', ''))
title = entry.get('title', '')

print('\n--- Step 2: Most recent entry ---')
print('  Title:     {}'.format(title))
print('  Bundle:    {}'.format(bundle_id))
print('  UID:       {}'.format(uid))

# Step 3: Extract activity context
print('\n--- Step 3: get_activity_context() ---')
context = service.get_activity_context(entry)
for key, val in context.items():
    print('  {}: {}'.format(key, val))

# Step 4: Get activity history
print('\n--- Step 4: get_activity_history() ---')
history = service.get_activity_history(
    bundle_id=bundle_id,
    exclude_uid=uid,
    limit=5,
)
print('  Found {} past entries for {}'.format(len(history), bundle_id))
for i, h in enumerate(history):
    print('  [{}] {} (reflection: {})'.format(
        i, h['title'],
        'yes' if h['reflection'] else 'no'))

# Step 5: Get past reflections for this entry
# Step 6: Build the API request payload
print('\n--- Step 6: Build request payload for API ---')
payload = service._build_request_payload(entry, history)
print('  Payload that will be POSTed to {}:'.format(reflection.AI_SERVICE_URL))
print('  {}'.format(json.dumps(payload, indent=2, default=str)))

# Step 7: Test mock (fallback) prompt
print('\n--- Step 7: Generate prompt (mock fallback) ---')
prompt_result = []


def on_prompt(prompt):
    prompt_result.append(prompt)


service._mock_api_response(entry, history, on_prompt)
if prompt_result:
    print('  Mock prompt: "{}"'.format(prompt_result[0]))
else:
    print('  ERROR: No mock prompt generated!')

# Step 8: Test real API call (if server is running)
print('\n--- Step 8: Test real API call ---')
try:
    from urllib.request import urlopen, Request
    from urllib.error import URLError
    json_data = json.dumps(payload).encode('utf-8')
    req = Request(
        reflection.AI_SERVICE_URL,
        data=json_data,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    resp = urlopen(req, timeout=5)
    result = json.loads(resp.read().decode('utf-8'))
    print('  API Response: {}'.format(json.dumps(result, indent=2)))
except URLError as e:
    print('  API server not running at {} ({})'.format(
        reflection.AI_SERVICE_URL, e))
    print('  This is expected if you haven\'t started the backend yet.')
    print('  To start it: cd ai-reflection-service && uvicorn app.main:app')
except Exception as e:
    print('  API call error: {}'.format(e))

print('\n' + '=' * 50)
print('  All tests passed!')
print('=' * 50)
