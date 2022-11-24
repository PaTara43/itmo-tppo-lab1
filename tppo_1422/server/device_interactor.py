"""This is device state monitor. It watches for device emulator file changes and sets a callback when changes occur."""

import asyncio
import logging
import pyinotify
import xmltodict

from constants import DEVICES

logger = logging.getLogger(__name__)


def get_device_names() -> dict:
    """
    Pass DEVICES constant.

    :return: DEVICES constant.

    """

    return DEVICES.keys()


def get_device_by_path(path: str) -> str:
    """
    Get device name by its path.

    :param path: Device path.

    :return: Device name

    """

    return {i for i in DEVICES if DEVICES[i] == path}.pop()


def set_device_state(device: str, target_states: dict) -> (bool, str):
    """
    Change device states.

    :param device: Device name to interact with
    :param target_states: New device state. Pass channels as keys and new states as values. E.g. {"ch1": "On"}

    :return: Tuple of success flag and message. True if successfully changed states, False if not.

    """

    logger.debug(f"Attempting to change states of device {device} to {target_states}.")

    if device not in DEVICES.keys():
        message: str = f"No device '{device}' found!"
        return False, message

    different: bool = False
    with open(DEVICES[device]) as fd:
        current_states = list(xmltodict.parse(fd.read()).values())[0]

    for target_attribute in target_states.keys():
        if target_attribute not in current_states.keys():
            message: str = (
                f"Attribute '{target_attribute}' not in device '{device}' attributes list "
                f"'{list(current_states.keys())}'!"
            )
            return False, message
        elif target_states[target_attribute] not in current_states[target_attribute]["possible_states"].split(", "):
            message = (
                f"State '{target_states[target_attribute]}' not in device '{device}' attribute "
                f"'{target_attribute}' possible states list "
                f"'{current_states[target_attribute]['possible_states'].split(', ')}'! "
            )
            return False, message
        elif target_states[target_attribute] != current_states[target_attribute]["state"]:
            current_states[target_attribute]["state"] = target_states[target_attribute]
            different = True

    if not different:
        message = f"No changes for device '{device}'."
        return False, message

    with open(DEVICES[device], "w") as fd:
        fd.write(xmltodict.unparse({device: current_states}, pretty=True))

    for i in current_states:
        current_states[i] = current_states[i]["state"]
    message = f"Successfully modified states of file '{device}'! New device states: '{current_states}'."
    return True, message


def get_device_state(device: str, attribute: str | None = None) -> (bool, dict | str):
    """
    Get device states from a device emulating file.

    :param device: Device name as in constants.py.
    :param attribute: Exact attribute of a device.

    :return: Device states as a dictionary or a device attribute state.

    """

    logger.debug(f"Reading device '{device}' states.")
    if device not in DEVICES.keys():
        success_flag: bool = False
        message: str = f"No device '{device}' found!"
    else:
        with open(DEVICES[device]) as fd:
            states = list(xmltodict.parse(fd.read()).values())[0]
        if attribute:
            if attribute not in states.keys():
                success_flag: bool = False
                message: str = f"No attribute '{attribute}' found for device '{device}'!"
            else:
                success_flag: bool = True
                message: str = states[attribute]["state"]
        else:
            for i in states:
                states[i] = states[i]["state"]
            success_flag: bool = True
            message: str = states

    return success_flag, str(message)


def watch_device_state(device: str, callback: any) -> None:
    """
    Starts a file state watcher. Each time a file modified - calls a `callback` function passed as an argument.

    :param device: Device to watch.
    :param callback: Callback class with a method to execute at file change.

    """

    try:
        loop = asyncio.get_event_loop()
        logger.debug("Creating WatchManager object.")
        wm = pyinotify.WatchManager()

        logger.debug("Setting up a notifier.")
        notifier = pyinotify.AsyncioNotifier(wm, loop, default_proc_fun=callback)

        logger.debug(f"Starting watcher for file '{device}'.")
        wm.add_watch(DEVICES[device], pyinotify.IN_CLOSE_WRITE)
        logger.info(f"Watcher for device '{device}' set!")
    except Exception as e:
        logger.error(f"Error in a Watch Manager: {e}")
        notifier.stop()


if __name__ == "__main__":

    class EventHandler(pyinotify.ProcessEvent):
        """
        Sample event handler for file change events.
        """

        def process_IN_CLOSE_WRITE(self, event):
            """
            Process file changed event.

            :param event: Python Event.

            """
            device = {i for i in DEVICES if DEVICES[i] == event.path}
            print(f"updates in {device.pop()}")

    logging.basicConfig(level=logging.INFO)
    dev = "relay"
    attr = "ch1"

    asyncio_loop = asyncio.get_event_loop()
    success_flag_, message_ = get_device_state(device=dev)
    logger.info(f"{success_flag_}, {message_}")
    success_flag_, message_ = get_device_state(device=dev, attribute=attr)
    logger.info(f"{success_flag_}, {message_}")
    watch_device_state(device=dev, callback=EventHandler())
    success_flag_, message_ = set_device_state(device=dev, target_states={"ch1": "ON", "ch2": "ON"})
    logger.info(f"{success_flag_}, {message_}")

    asyncio_loop.run_forever()
