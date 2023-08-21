from typing import Dict, Any, Optional
import socket
from zeroconf import ServiceListener, Zeroconf, ServiceBrowser


class MyListener(ServiceListener):
    server_ip: Optional[str]
    last_fetched_message: Optional[Dict[str, Any]]
    last_posted_thought: Optional[str]

    def __init__(self) -> None:
        self.server_ip = None

    def remove_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
        print(f"Service {name} removed")

    def add_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
        info = zeroconf.get_service_info(type, name)
        print(f"Service {name} added, service info: {info}")
        if info.addresses:
            self.server_ip = socket.inet_ntoa(info.addresses[0])
            print(f"Server IP updated: {self.server_ip}")
        else:
            print("No addresses found for the service")

    def update_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
        info = zeroconf.get_service_info(type, name)
        print(f"Service {name} updated, service info: {info}")
        if info.addresses:
            self.server_ip = socket.inet_ntoa(info.addresses[0])
            print(f"Server IP updated: {self.server_ip}")
        else:
            print("No addresses found for the updated service")


zeroconf = Zeroconf()
listener = MyListener()
browser = ServiceBrowser(zeroconf, "_beatlinkdata._tcp.local.", listener)
