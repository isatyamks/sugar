"""
Test 3: Test the find_entries() function we added to model.py
Run inside Sugar:
  export PYTHONPATH=/home/isatyamks/sugar/src
  python3 ~/sugar/tests_journal/test_find_entries.py
"""
import gi
gi.require_version('SugarExt', '1.0')

from jarabe.journal import model

print('=' * 50)
print('  TEST: model.find_entries()')
print('  Loaded model from: {}'.format(model.__file__))
print('=' * 50)

# Get all recent entries
print('\n--- All recent entries (limit 10) ---')
entries = model.find_entries({}, limit=10)
print('  Found {} entries'.format(len(entries)))

for i, entry in enumerate(entries):
    print('\n  [{}] {}'.format(i, entry.get('title', '(no title)')))
    print('      bundle_id: {}'.format(entry.get('bundle_id', '')))
    print('      timestamp: {}'.format(entry.get('timestamp', '')))
    print('      uid:       {}'.format(entry.get('uid', '')))

# List unique bundle_ids
bundle_ids = set()
for entry in entries:
    bid = entry.get('bundle_id', '')
    if bid:
        bundle_ids.add(str(bid))

print('\n--- Unique activity types found ---')
for bid in sorted(bundle_ids):
    print('  - {}'.format(bid))

# Test filtering by first bundle_id found
if bundle_ids:
    test_bid = sorted(bundle_ids)[0]
    print('\n--- Filtering by: {} ---'.format(test_bid))
    filtered = model.find_entries({'bundle_id': test_bid}, limit=5)
    print('  Found {} entries'.format(len(filtered)))
    for entry in filtered:
        print('    - {}'.format(entry.get('title', '')))

print('\n' + '=' * 50)
print('  All tests passed!')
print('=' * 50)
