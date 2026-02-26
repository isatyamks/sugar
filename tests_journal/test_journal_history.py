"""
Test 1: Query the Sugar Journal Datastore and print all entries.
Run inside Sugar: python3 ~/sugar/tests_journal/test_journal_history.py
"""
import dbus

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

entries, count = ds.find({}, properties, byte_arrays=True)

print('=' * 50)
print('  SUGAR JOURNAL HISTORY')
print('  Total entries: {}'.format(count))
print('=' * 50)

for i, entry in enumerate(entries):
    print('\n--- Entry {} ---'.format(i + 1))
    print('  Title:       {}'.format(entry.get('title', '')))
    print('  Bundle ID:   {}'.format(entry.get('bundle_id', '')))
    print('  MIME Type:   {}'.format(entry.get('mime_type', '')))
    print('  Timestamp:   {}'.format(entry.get('timestamp', '')))
    print('  Activity ID: {}'.format(entry.get('activity_id', '')))
    print('  UID:         {}'.format(entry.get('uid', '')))
    desc = str(entry.get('description', ''))
    if desc:
        print('  Description: {}...'.format(desc[:80]))

print('\n' + '=' * 50)
print('  Done.')
print('=' * 50)
