"""
This is a main file of a UDP socket server for communicating with clients and interacting with a sample IoT device.
"""

import asyncio
import logging
import nest_asyncio
import pyinotify
import sys

from ast import literal_eval

from constants import DEFAULT_SERVER_ADDRESS
from device_interactor import (
    get_device_state,
    watch_device_state,
    set_device_state,
    get_device_names,
    get_device_by_path,
)

logger = logging.getLogger(__name__)
nest_asyncio.apply()


class IoTServerProtocol:
    """
    asyncio-protocol Datagram Protocol instance. Based on a Base Protocol.
        https://docs.python.org/3/library/asyncio-protocol.html#datagram-protocols
        https://docs.python.org/3/library/asyncio-protocol.html#base-protocol

    """

    def __init__(self):
        """
        Initialize class attributes
        """

        self.subscribers_list: dict = {}
        self.transport = None
        for dev in get_device_names():
            self.subscribers_list[dev] = {k: [] for k in literal_eval(get_device_state(device=dev)[1])}
        self.current_device_states: dict = {d: literal_eval(get_device_state(d)[1]) for d in get_device_names()}

    def connection_made(self, transport):
        """
        Called when a connection is made.
            https://docs.python.org/3/library/asyncio-protocol.html#asyncio.BaseProtocol.connection_made

        :param transport: UDP transport.

        """

        self.transport = transport

    def datagram_received(self, data, addr) -> None:
        """
        Called when a datagram is received.
            https://docs.python.org/3/library/asyncio-protocol.html#asyncio.DatagramProtocol.datagram_received

        :param data: A bytes object containing the incoming data.
        :param addr: The address of the peer sending the data.

        """

        request = data.decode()
        logger.debug(f"Received request '{request}' from address '{addr}'.")
        request_list = request.split(" ")
        if request_list[0] == "get":
            self._process_get(request_list, addr)
        elif request_list[0] == "set":
            self._process_set(request_list, addr)
        elif request_list[0] == "subscribe":
            self._process_subscribe(request_list, addr)
        elif request_list[0] == "unsubscribe":
            self._process_unsubscribe(addr)
        else:
            message = "Invalid request command. Choose from get|set|subscribe|unsubscribe"
            logger.error(message)
            response = {"Success": False, "Message": message}
            logger.debug(f"Sending response '{response}' to '{addr}'.")
            self.transport.sendto(str(response).encode(), addr)

    def _process_get(self, message_list: list, addr: tuple) -> None:
        """
        Process get request.

        :param message_list: Received message as a list.
        :param addr: Source address.

        """

        try:
            if len(message_list) == 2:
                success_flag, message = get_device_state(device=message_list[1])
            elif len(message_list) == 3:
                success_flag, message = get_device_state(device=message_list[1], attribute=message_list[2])
            else:
                success_flag = False
                message = "Invalid request. Get request should contain device name and optionally it's attribute"
        except Exception as e:
            success_flag = False
            message = f"Error processing 'get' request: {e}."
        finally:
            self._send_response(success_flag=success_flag, message=message, addr=addr)

    def _process_set(self, message_list: list, addr: tuple) -> None:
        """
        Process set request.

        :param message_list: Received message as a list.
        :param addr: Source address.

        """

        try:
            if len(message_list) >= 4 and len(message_list) % 2 == 0:
                target_states: dict = {}
                i: int = 2
                while i < len(message_list):
                    target_states[message_list[i]] = message_list[i + 1]
                    i = i + 2
                success_flag, message = set_device_state(device=message_list[1], target_states=target_states)
            else:
                success_flag: bool = False
                message: str = (
                    "Device set message should contain device name and attributes and states space "
                    "separated (att1 val1 attr2 val 2). "
                )
        except Exception as e:
            success_flag = False
            message = f"Error processing 'set' request: {e}."
        finally:
            self._send_response(success_flag=success_flag, message=message, addr=addr)

    def _process_subscribe(self, message_list: list, addr: tuple) -> None:
        """
        Process subscribe request.

        :param message_list: Received message as a list.
        :param addr: Source address.

        """

        try:
            subscribed_attrs: list = []
            if len(message_list) == 1:
                success_flag: bool = False
                message: str = (
                    "No device provided. Provide a device with its attributes. E.g. subscribe dev attr1 " "attr2."
                )
            elif len(message_list) == 2:
                success_flag: bool = False
                message: str = (
                    f"No attributes of device '{message_list[1]}' provided. Provide a device with its "
                    f"attributes. E.g. subscribe dev attr1 attr2."
                )
            else:
                for i in range(2, len(message_list)):
                    if addr in self.subscribers_list[message_list[1]][message_list[i]]:
                        raise Exception(f"Already subscribed to one or more attributes of device '{message_list[1]}'.")
                    self.subscribers_list[message_list[1]][message_list[i]].append(addr)
                    subscribed_attrs.append(message_list[i])

                success_flag: bool = True
                message = f"Subscribed '{subscribed_attrs}' attribute(s) of device '{message_list[1]}'."
        except KeyError:
            success_flag: bool = False
            message = f"Error in device name or attribute name."
        except Exception as e:
            success_flag = False
            message = f"Error processing 'subscribe' request: {e}."
        finally:
            self._send_response(success_flag=success_flag, message=message, addr=addr)

    def _process_unsubscribe(self, addr: tuple) -> None:
        """
        Process unsubscribe request. Unsubscribes from all the notifications.

        :param addr: Source address.

        """

        try:
            for attributes in self.subscribers_list.values():
                for dev_list in attributes.values():
                    if addr in dev_list:
                        dev_list.remove(addr)
            success_flag: bool = True
            message = f"Unsubscribed from all events of all devices."
        except Exception as e:
            success_flag = False
            message = f"Error processing 'unsubscribe' request: {e}."
        finally:
            self._send_response(success_flag=success_flag, message=message, addr=addr)

    def _send_response(self, success_flag: bool, message: str, addr: tuple):
        """
        Send response to client.

        :param success_flag: Processed query success flag.
        :param message: Accompanying message.
        :param addr: Address to send response to.

        """

        if not success_flag:
            logger.error(message)
        response = {"Success": success_flag, "Message": message}
        logger.debug(f"Sending response '{response}' to '{addr}'.")
        self.transport.sendto(str(response).encode(), addr)


async def main(host: str, port: int):
    """
    Start UDP server, start device_interactor module.

    :param host: Server host.
    :param port: Server port.

    """

    try:
        loop = asyncio.get_running_loop()
        logger.info(f"Starting UDP server at {host}:{port}.")
        transport, protocol = await loop.create_datagram_endpoint(lambda: IoTServerProtocol(), local_addr=(host, port))

        class EventHandler(pyinotify.ProcessEvent):
            """
            Handle device updates

            """

            def process_IN_CLOSE_WRITE(self, event):

                try:
                    device = get_device_by_path(event.path)
                    logger.debug(f"Changes in device {device}")
                    new_device_states: dict = literal_eval(get_device_state(device)[1])

                    for attr in new_device_states.keys():
                        if new_device_states[attr] != protocol.current_device_states[device][attr]:
                            for address in protocol.subscribers_list[device][attr]:
                                notification = (
                                    f"Updates in device '{device}' attribute '{attr}'! "
                                    f"'{protocol.current_device_states[device][attr]}' -> "
                                    f"'{new_device_states[attr]}'"
                                )
                                notification_ = {"Success": True, "Message": notification}
                                logger.debug(f"Sending notification '{notification_}' to '{address}'.")
                                transport.sendto(str(notification_).encode(), address)

                            protocol.current_device_states[device][attr] = new_device_states[attr]

                except Exception as err:
                    logger.error(f"Error processing device update: {err}")

        logger.debug("Starting device watchers.")
        for dev in get_device_names():
            watch_device_state(device=dev, callback=EventHandler())

        loop.run_forever()
    except Exception as e:
        logger.error(f"Error running server: {e}.")
        exit()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    n = len(sys.argv)
    if n == 3:
        asyncio.run(main(sys.argv[1], int(sys.argv[2])))
    elif n == 1:
        asyncio.run(main(DEFAULT_SERVER_ADDRESS[0], DEFAULT_SERVER_ADDRESS[1]))
    else:
        raise IOError("Incorrect number of arguments! Either pass server host and port or pass nothing.")
