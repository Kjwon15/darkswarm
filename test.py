import time

from darkswarm.manager import SwarmManager


sm = SwarmManager(
    {
        'malformed': None,
        'sakura': 'ssh://sakura',
        'shion': 'ssh://shion',
    },
    {
        'general': {
            'size': 2,
            'generic_resources': None,
        },
        'gpu': {
            'size': 1,
            'generic_resources': None,
        }
    }
)

service = sm.get_service('general', ['curl', 'https://icanhazip.com'])

time.sleep(10)

print('Cleaning up')
sm.cleanup()

# service.remove()

while service.tasks()[0]['Status']['State'] != 'complete':
    print('wait')
    time.sleep(1)

print(b''.join(service.logs(stdout=True)).decode())
service.remove()
