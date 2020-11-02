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
        "mounts": ["/var/nfs:/nfs"],
        "constraints": ["node.role==worker"],
      },
      "gpu": {
        "size": 1,
        "cpu_reservation": 1_000_000_000,
        "mem_reservation": 1_024_000,
        "generic_resources": {
          "GPU": 3000,
        }
      }
    }
    """

    MAX_RETRY = 20

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
        pool = self.pool[t]
        for _ in range(self.MAX_RETRY):
            service = pool.pop(0)
            task = service.tasks()[0]
            if task['Status']['State'] != 'running':
                print(f'skipping {service.id}...')
                time.sleep(1)
                pool.append(service)
                continue
            break
        else:
            # TODO: Make custom exception
            raise Exception()

        containerid = task['Status']['ContainerStatus']['ContainerID']
        nodeid = task['NodeID']
        node = self.cli.nodes.get(nodeid)
        hostname = node.attrs['Description']['Hostname']

        print(f'Run on {hostname} {containerid}')

        cli = self.hosts[hostname]
        container = cli.containers.get(containerid)

        self._exec_container(container, cmd)

        self._prepare_type(t)

        return service

    def get_container(self, t: str, cmd: List[str]):
        pool = self.pool[t]

        container = pool.pop(0)

        self._exec_container(container, cmd)

        self._prepare_type(t)

        return container

    def cleanup(self):
        if self.mode == Mode.SWARM:
            for service in (
                    service
                    for services in self.pool.values()
                    for service in services):
                service.remove()
        elif self.mode == Mode.MANUAL:
            # TODO: remove containers
            raise NotImplementedError()

    @staticmethod
    def _exec_container(container, cmd: List[str]):
        container.exec_run(
            cmd='sh -c "echo $cmd > /tmp/cmd.json"',
            environment={
                'cmd': json.dumps(cmd),
            }
        )

    def _prepare(self):
        for t in self.types.keys():
            self._prepare_type(t)

    def _prepare_type(self, t):
        for _ in range(self.types[t]['size'] - len(self.pool[t])):
            if self.mode == Mode.SWARM:
                service_name = f'darkswarm-{t}-{uuid.uuid4().hex}'

                rp = docker.types.RestartPolicy(condition='none')

                cpu_reservation = self.types[t].get('cpu_reservation')
                mem_reservation = self.types[t].get('cpu_reservation')
                generic_resources = self.types[t].get('cpu_reservation')
                resources = docker.types.Resources(
                    cpu_reservation=cpu_reservation,
                    mem_reservation=mem_reservation,
                    generic_resources=generic_resources)

                mounts = self.types[t].get('mounts')
                constraints = self.types[t].get('constraints')

                service = self.cli.services.create(
                    name=service_name,
                    image=self.baseimage,
                    command=self.command,
                    restart_policy=rp,
                    resources=resources,
                    mounts=mounts,
                    constraints=constraints,
                )
                self.pool[t].append(service)
            elif self.mode == Mode.MANUAL:
                raise NotImplementedError
