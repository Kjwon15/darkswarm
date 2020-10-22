import json
import time
import uuid

from typing import Dict, List, Optional
from enum import Enum
from pprint import pprint

import docker


class Mode(Enum):
    SWARM = 1
    MANUAL = 2


class SwarmManager():

    def __init__(
            self,
            hosts: Dict[str, str],
            baseimage: Optional[str] = None,
            command: Optional[str] = None,
            mode: Optional[Mode] = Mode.SWARM,
            size: Optional[int] = 2):

        self.baseimage = baseimage or 'kjwon15/wait'
        self.command = command

        self.cli = docker.from_env()
        self.hosts = {
            hostname: docker.DockerClient(base_url=base_url)
            for hostname, base_url in hosts.items()
        }
        self.mode = mode
        self.pool = []
        self.size = size

        self._prepare()

    def get_service(self, cmd: List[str]):
        while True:
            service = self.pool.pop(0)
            task = service.tasks()[0]
            if task['Status']['State'] != 'running':
                print(f'skipping {service.id}...')
                time.sleep(1)
                self.pool.append(service)
                continue
            break
        containerid = task['Status']['ContainerStatus']['ContainerID']
        nodeid = task['NodeID']
        node = self.cli.nodes.get(nodeid)
        hostname = node.attrs['Description']['Hostname']

        print(f'Run on {hostname} {containerid}')

        cli = self.hosts[hostname]
        container = cli.containers.get(containerid)

        container.exec_run(
            cmd='sh -c "echo $cmd > /tmp/cmd.json"',
            environment={
                'cmd': json.dumps(cmd),
            }
        )

        return service

    def cleanup(self):

        for service in self.pool:
            service.remove()

    def _prepare(self):
        for _ in range(self.size - len(self.pool)):
            if self.mode == Mode.SWARM:
                rp = docker.types.RestartPolicy(condition='none')
                service_name = f'darkswarm-{uuid.uuid4().hex}'

                service = self.cli.services.create(
                    name=service_name,
                    image=self.baseimage,
                    command=self.command,
                    restart_policy=rp,
                )
                self.pool.append(service)
            elif self.mode == Mode.MANUAL:
                raise NotImplementedError
