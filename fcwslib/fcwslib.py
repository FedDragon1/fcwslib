import os
import time
import uuid
import json
import asyncio

import websockets
from rich.console import Console
from rich.traceback import install

__all__ = ["Handler", "Server"]
console = Console()

install(console=console)


class Handler(object):
    def __init__(self, websocket, path) -> None:
        self.websocket = websocket
        self.path = path

    async def _on_connect(self) -> None:
        await self.subscribe("PlayerMessage")
        await self.on_connect()
        console.log("receive")
        while True:
            try:
                message = await self.websocket.recv()
            except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK):
                await self._on_disconnect()
                for task in asyncio.all_tasks():
                    task.cancel()
                break
            else:
                await self._on_receive(message)

    async def _on_disconnect(self) -> None:
        await self.on_disconnect()

    async def _on_receive(self, message: str) -> None:
        await self.on_receive(message)

    async def on_connect(self) -> None:
        console.log("Connected.")
        # while True:
        #     await self.send_command(
        #         'tellraw @a {"rawtext":[{"text": "Hello, world!"}]}'
        #     )
        #     await asyncio.sleep(1)
        await self.send_command(
            'tellraw @a {"rawtext":[{"text": "Hello, world!"}]}'
        )
        await asyncio.sleep(1)

        asyncio.create_task(self.on_connect())

    async def on_disconnect(self) -> None:
        console.log("Disconnected.")

    async def on_receive(self, message: str) -> None:
        console.log("Received {}".format(message))

    async def send(self, message: str) -> None:
        await self.websocket.send(message)

    async def send_command(self, command: str) -> None:
        response = {
            "header": build_header("commandRequest"),
            "body": {
                "origin": {"type": "player"},
                "commandLine": command,
                "version": 1,
            },
        }

        response = json.dumps(response)
        await self.send(response)

    async def subscribe(self, event_name: str) -> None:
        response = {
            "header": build_header("subscribe"),
            "body": {"eventName": str(event_name)},
        }

        response = json.dumps(response)

        await self.send(response)

    async def unsubscribe(self, event_name: str) -> None:
        response = {
            "header": build_header("dissubscribe"),
            "body": {"eventName": str(event_name)},
        }

        response = json.dumps(response)
        await self.send(response)


class Server(object):
    def __init__(self, host: str = "localhost", port: int = 8000) -> None:
        self.host = host
        self.port = port
        self._handlers = []

    def add_handlers(self, handler) -> None:
        self._handlers.append(handler)

    def remove_handlers(self, handler) -> None:
        self._handlers.remove(handler)

    async def run_forever(self) -> None:
        # start_server = websockets.serve(self._on_connect, self.host, self.port)
        # asyncio.get_event_loop().run_until_complete(start_server)
        # asyncio.get_event_loop().run_forever()
        async with websockets.serve(self._on_connect, self.host, self.port):
            console.log(f"Server opened at {self.host}:{self.port}")
            await asyncio.Future()

    async def _on_connect(self, websocket, path) -> None:
        for handler in self._handlers:
            await handler(websocket, path)._on_connect()

def build_header(purpose: str, request_id: str = None) -> dict:
    if request_id is None:
        request_id = str(uuid.uuid4())

    return {
        "requestId": request_id,
        "messagePurpose": purpose,
        "version": 1,
        "messageType": "commandRequest",
    }


async def main():
    server = Server(port=8000)
    server.add_handlers(Handler)
    await server.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
