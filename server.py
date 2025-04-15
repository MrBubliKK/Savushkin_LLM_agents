import argparse
from sc_kpm import ScServer
from search_module import SearchModule


from pathlib import Path

import tkinter as tk
from tkinter import scrolledtext, Button, Entry, Label, END
import os
from together import Together  # Import TogetherAI library

from sc_kpm.utils.action_utils import execute_agent
from sc_kpm.utils.common_utils import create_link
from sc_kpm.identifiers import Idtf, CommonIdentifiers

from dataclasses import dataclass

dataclass(frozen=True)
class CallIdentifiers:
    ACTION_CALL_AGENT: Idtf = "action_call_agent"

SC_SERVER_PROTOCOL = "protocol"
SC_SERVER_HOST = "host"
SC_SERVER_PORT = "port"

SC_SERVER_PROTOCOL_DEFAULT = "ws"
SC_SERVER_HOST_DEFAULT = "localhost"
SC_SERVER_PORT_DEFAULT = "8090"

import argparse
from sc_kpm import ScServer
from search_module import SearchModule


from pathlib import Path

SC_SERVER_PROTOCOL = "protocol"
SC_SERVER_HOST = "host"
SC_SERVER_PORT = "port"

SC_SERVER_PROTOCOL_DEFAULT = "ws"
SC_SERVER_HOST_DEFAULT = "localhost"
SC_SERVER_PORT_DEFAULT = "8090"


def main(args: dict):
    server = ScServer(
        f"{args[SC_SERVER_PROTOCOL]}://{args[SC_SERVER_HOST]}:{args[SC_SERVER_PORT]}")

    with server.connect():
        modules = [
            SearchModule()
        ]
        server.add_modules(*modules)
        with server.register_modules():
            server.serve()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--protocol', type=str, dest=SC_SERVER_PROTOCOL, default=SC_SERVER_PROTOCOL_DEFAULT, help="Sc-server protocol")
    parser.add_argument(
        '--host', type=str, dest=SC_SERVER_HOST, default=SC_SERVER_HOST_DEFAULT, help="Sc-server host")
    parser.add_argument(
        '--port', type=int, dest=SC_SERVER_PORT, default=SC_SERVER_PORT_DEFAULT, help="Sc-server port")
    args = parser.parse_args()

    main(vars(args))