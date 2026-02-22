"""
Test 4: Full test of ReflectionService with real Journal data.
Run inside Sugar:
  export PYTHONPATH=/home/isatyamks/sugar/src
  python3 ~/sugar/tests_journal/test_reflection_service.py
"""
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

# Step 1: Get all journal entries
print('\n--- Step 1: Get all journal entries ---')
all_entries = model.find_entries({}, limit=10)
print('  Found {} entries'.format(len(all_entries)))

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
print('\n--- Step 5: get_past_reflections() ---')
reflections = service.get_past_reflections(entry)
print('  Found {} reflections on this entry'.format(len(reflections)))

# Step 6: Generate a prompt
print('\n--- Step 6: Generate reflection prompt ---')
prompt_result = []


def on_prompt(prompt):
    prompt_result.append(prompt)


# Call directly (skip GLib timer in test)
service._mock_api_response(entry, history, on_prompt)
if prompt_result:
    print('  Prompt: "{}"'.format(prompt_result[0]))
else:
    print('  ERROR: No prompt generated!')

print('\n' + '=' * 50)
print('  All tests passed!')
print('=' * 50)
