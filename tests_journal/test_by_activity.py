"""
Test 2: Query entries for a specific activity type.
Run inside Sugar: python3 ~/sugar/tests_journal/test_by_activity.py
"""
import dbus
import sys

bundle_id = sys.argv[1] if len(sys.argv) > 1 else ''

bus = dbus.SessionBus()
ds = dbus.Interface(
    bus.get_object(
        'org.laptop.sugar.DataStore',
        '/org/laptop/sugar/DataStore'),
    'org.laptop.sugar.DataStore')

properties = [
    'title', 'bundle_id', 'mime_type',
    'timestamp', 'description', 'activity_id', 'uid'
]

# If bundle_id provided, filter by it
if bundle_id:
    query = {'bundle_id': bundle_id}
    print('Searching for bundle_id: {}'.format(bundle_id))
else:
    query = {}
    print('No bundle_id specified. Showing all entries.')
    print('Usage: python3 test_by_activity.py org.laptop.Write')

entries, count = ds.find(query, properties, byte_arrays=True)

print('=' * 50)
print('  Found {} entries'.format(count))
print('=' * 50)

for i, entry in enumerate(entries):
    print('\n--- Entry {} ---'.format(i + 1))
    print('  Title:     {}'.format(entry.get('title', '')))
    print('  Bundle:    {}'.format(entry.get('bundle_id', '')))
    print('  Timestamp: {}'.format(entry.get('timestamp', '')))

print('\n  Done.')
