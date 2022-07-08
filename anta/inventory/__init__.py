#!/usr/bin/python
# coding: utf-8 -*-

"""
Inventory Module for ANTA.
"""

import logging
import ssl
from socket import setdefaulttimeout

import yaml
from jinja2 import Template
from jsonrpclib import ProtocolError, Server, jsonrpc
from netaddr import IPNetwork, IPAddress
from pydantic import ValidationError
from yaml.loader import SafeLoader

from .models import AntaInventoryInput, InventoryDevice
from .exceptions import InventoryRootKeyErrors, InventoryIncorrectSchema, InventoryUnknownFormat

# pylint: disable=W0212
ssl._create_default_https_context = ssl._create_unverified_context

class AntaInventory():
    """Inventory Abstraction for ANTA framework.

    Inventory file example:
    ----------------------
    >>> print(inventory.yml)
    >>> anta_inventory:
    >>>   hosts:
    >>>     - hosts: 1.1.1.1
    >>>     - host: 2.2.2.2
    >>>   networks:
    >>>     - network: 10.0.0.0/8
    >>>     - network: 192.168.0.0/16
    >>>   ranges:
    >>>     - start: 10.0.0.1
    >>>       end: 10.0.0.11

    Inventory Output:
    ------------------
    >>> test = AntaInventory(inventory_file='examples/inventory.yml',username='ansible', password='ansible', auto_connect=True)
    >>> test.inventory_get()
    >>> [
    >>>     "InventoryDevice(host=IPv4Address('192.168.0.17')",
    >>>     "username='ansible'",
    >>>     "password='ansible'",
    >>>     "session=<ServerProxy for ansible:ansible@192.168.0.17/command-api>",
    >>>     "url='https://ansible:ansible@192.168.0.17/command-api'",
    >>>     "established=True",

    >>>     "InventoryDevice(host=IPv4Address('192.168.0.2')",
    >>>     "username='ansible'",
    >>>     "password='ansible'",
    >>>     "session=None",
    >>>     "url='https://ansible:ansible@192.168.0.2/command-api'",
    >>>     "established=False"
    >>> ]
    """

    # Root key of inventory part of the inventory file
    INVENTORY_ROOT_KEY = 'anta_inventory'
    # Template to build eAPI connection URL
    EAPI_SESSION_TPL = 'https://{{device_username}}:{{device_password}}@{{device}}/command-api'
    # Supported Output format
    INVENTORY_OUTPUT_FORMAT = ['native', 'json']

    def __init__(self, inventory_file: str, username: str, password: str, auto_connect: bool = True):
        """Class constructor.

        Args:
            inventory_file (str): Path to inventory YAML file where user has described his inputs
            username (str): Username to use to connect to devices
            password (str): Password to use to connect to devices
            auto_connect (bool, optional): Automatically build eAPI context for every devices. Defaults to True.
        """
        self._username = username
        self._password = password
        self._inventory = []

        with open(inventory_file, 'r', encoding='utf8') as f:
            data = yaml.load(f, Loader=SafeLoader)

        # Load data using Pydantic
        try:
            self._read_inventory = AntaInventoryInput( **data[self.INVENTORY_ROOT_KEY] )
        except KeyError as exc:
            logging.error(f'Inventory root key is missing: {self.INVENTORY_ROOT_KEY}')
            raise InventoryRootKeyErrors(
                f'Inventory root key ({self.INVENTORY_ROOT_KEY}) is not defined in your inventory') from exc
        except ValidationError as exc:
            logging.error('Inventory data are not compliant with inventory models')
            raise InventoryIncorrectSchema(
                'Inventory is not following schema') from exc

        # Read data from input
        if self._read_inventory.dict()['hosts'] is not None:
            self._inventory_read_hosts()
        if self._read_inventory.dict()['networks'] is not None:
            self._inventory_read_networks()
        if self._read_inventory.dict()['ranges'] is not None:
            self._inventory_read_ranges()

        # Create RPC connection for all devices
        if auto_connect:
            self.sessions_create()

    def _is_ip_exist(self, ip: str):
        """Check if an IP is part of the current inventory.

        Args:
            ip (str): IP address to search in our inventory

        Returns:
            bool: True if device is in our inventory, False if not
        """
        if ip in [str(dev.host) for dev in self._inventory ]:
            return True
        return False

    def device_get(self, host_ip):
        """Get device information from a given IP.

        Args:
            host_ip (str): IP address of the device

        Returns:
            InventoryDevice: Device information
        """
        if self._is_ip_exist(host_ip):
            return [dev for dev in self._inventory if str(dev.host) == str(host_ip)][0]
        return None

    def _session_build_path(self, host: str, username: str, password: str):
        """Construct URL to reach device using eAPI.

        Jinja2 render to build URL to use for eAPI session.

        Args:
            host (str): IP Address of the device to target in the eAPI session
            username (str): Username for authentication
            password (str): Password for authentication

        Returns:
            str: String to use to create eAPI session
        """
        session_template = Template(self.EAPI_SESSION_TPL)
        return session_template.render(
            device=host,
            device_username=username,
            device_password=password
         )

    def _session_create(self, device : InventoryDevice, timeout: int = 5):
        """Create eAPI RPC session to Arista EOS devices.

        Args:
            device (InventoryDevice): Device information based on InventoryDevice structure
            timeout (int, optional): Device timeout to declare host as down. Defaults to 5.

        Returns:
            InventoryDevice: Updated device structure with its RPC connection
        """
        connection = Server(device.url)
        # Check connectivity
        try:
            setdefaulttimeout(timeout)
            connection.runCmds(1,['show version'])
        # pylint: disable=W0702
        except:
            logging.error(f'Service not running on device {device.host}')
            device.session = None
        else:
            device.established = True
            device.session = connection
        return device

    def session_create(self, host_ip: str):
        """Get session of a device.

        If device has already a session, function only returns active session, if not, try to build a new session

        Args:
            host_ip (str): IP address of the device

        Returns:
            bool: True if update succeed, False if not
        """
        device = [ dev for dev in self._inventory if str(dev.host) == str(host_ip)][0]
        if not device.established and self._is_ip_exist(host_ip):
            logging.debug('trying to connect to device')
            device = self._session_create(device=device)
            # pylint: disable=W0104
            [device if dev.host == device.host else dev for dev in self._inventory]
            return True
        return False

    def session_get(self, host_ip: str):
        """Expose RPC session of a given host from our inventory.

        Provide RPC session if the session exists, if not, it returns None

        Args:
            host_ip (str): IP address of the host to match

        Returns:
            jsonrpclib.Server: Instance to the device. None if session does not exist
        """
        device = self.device_get(host_ip=host_ip)
        if device is None:
            return None
        return device.session

    def sessions_create(self):
        """Helper to build RPC sessions to all devices"""
        for device in self._inventory:
            self.session_create(host_ip=device.host)

    def _inventory_add_device(self, host_ip):
        """Add a InventoryDevice to final inventory.

        Create InventoryDevice and append to existing inventory

        Args:
            host_ip (str): IP address of the host
        """
        device = InventoryDevice(
            host=host_ip,
            username=self._username,
            password=self._password,
            url=self._session_build_path(
                host=host_ip,
                username=self._username,
                password=self._password
            )
        )
        self._inventory.append(device)

    def _inventory_read_hosts(self):
        """Read input data from hosts section and create inventory structure.

        Build InventoryDevice structure for all hosts under hosts section
        """
        for host in self._read_inventory.hosts:
            self._inventory_add_device(host_ip=host.host)

    def _inventory_read_networks(self):
        """Read input data from networks section and create inventory structure.

        Build InventoryDevice structure for all IPs available in each declared subnet
        """
        for network in self._read_inventory.networks:
            for host_ip in IPNetwork(str(network.network)):
                self._inventory_add_device(host_ip=host_ip)

    def _inventory_read_ranges(self):
        """Read input data from ranges section and create inventory structure.

        Build InventoryDevice structure for all IPs available in each declared range
        """
        for range_def in self._read_inventory.ranges:
            range_increment = IPAddress(str(range_def.start))
            range_stop = IPAddress(str(range_def.end))
            while range_increment <= range_stop:
                self._inventory_add_device(host_ip=str(range_increment))
                range_increment += 1

    def inventory_get(self, format_out: str = 'native', established_only: bool = True):
        """inventory_get Expose device inventory.

        Provides inventory has a list of InventoryDevice objects. If requried, it can be exposed in JSON format. Also, by default expose only active devices.

        Args:
            format (str, optional): Format output, can be native or JSON. Defaults to 'native'.
            established_only (bool, optional): Allow to expose also unreachable devices. Defaults to True.

        Returns:
            List: List of InventoryDevice
        """
        if format_out not in ['native', 'json']:
            raise InventoryUnknownFormat(
                f'Unsupported inventory format: {format_out}. Only supported format are: {self.INVENTORY_OUTPUT_FORMAT}')

        if established_only:
            devices = [dev for dev in self._inventory if dev.established]
        else:
            devices = self._inventory

        if format_out == 'json':
            return [dev.dict() for dev in devices]
        return devices
