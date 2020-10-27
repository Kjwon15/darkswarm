import json
import time
import uuid

from collections import defaultdict
from typing import Dict, List, Optional
from enum import Enum

import docker


class Mode(Enum):
    SWARM = 1
    MANUAL = 2


class SwarmManager():
    """
    :arg: types (Dict[str, Options])
    {
      "general": {
        "size": 3,
        "generic_resources": None,
      },
      "gpu": {
        "size": 1,
        "generic_resources": {
          "GPU": 3000,
        }
      }
    }
    """

    def __init__(
            self,
            hosts: Dict[str, str],
            types: Dict[str, Dict],
            baseimage: Optional[str] = None,
            command: Optional[str] = None,
            mode: Optional[Mode] = Mode.SWARM):

        self.baseimage = baseimage or 'kjwon15/wait'
        self.command = command

        self.cli = docker.from_env()
        self.hosts = {
            hostname: docker.DockerClient(base_url=base_url)
            for hostname, base_url in hosts.items()
        }
        self.mode = mode
        self.pool = defaultdict(list)
        self.types = types

        self._prepare()

    def get_service(self, t: str, cmd: List[str]):
        while True:
            service = self.pool[t].pop(0)
            task = service.tasks()[0]
            if task['Status']['State'] != 'running':
                print(f'skipping {service.id}...')
                time.sleep(1)
                self.pool[t].append(service)
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

        self._prepare_type(t)

        return service

    def cleanup(self):

        for service in (
                service
                for services in self.pool.values()
                for service in services):
            service.remove()

    def _prepare(self):
        for t in self.types.keys():
            self._prepare_type(t)

    def _prepare_type(self, t):
        for _ in range(self.types[t]['size'] - len(self.pool[t])):
            if self.mode == Mode.SWARM:
                service_name = f'darkswarm-{t}-{uuid.uuid4().hex}'

                rp = docker.types.RestartPolicy(condition='none')
                resources = docker.types.Resources(
                    generic_resources=self.types[t]['generic_resources'])

                service = self.cli.services.create(
                    name=service_name,
                    image=self.baseimage,
                    command=self.command,
                    restart_policy=rp,
                    resources=resources,
                )
                self.pool[t].append(service)
            elif self.mode == Mode.MANUAL:
                raise NotImplementedError
