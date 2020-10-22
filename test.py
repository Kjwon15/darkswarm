import time

from darkswarm.manager import SwarmManager


sm = SwarmManager(
    {
        'malformed': None,
        'sakura': 'ssh://sakura',
        'shion': 'ssh://shion',
    },
)

service = sm.get_service(['curl', 'https://icanhazip.com'])

sm.cleanup()

# service.remove()

while service.tasks()[0]['Status']['State'] != 'complete':
    print('wait')
    time.sleep(1)

print(b''.join(service.logs(stdout=True)).decode())
service.remove()
