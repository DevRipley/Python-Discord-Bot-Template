import asyncio

from classes.discordbot import DiscordBot
from classes.utilities import cogs_directory, cogs_manager, load_config, reload_views

from discord.ext import commands
from logging import DEBUG as LOG_DEBUG, INFO as LOG_INFO, WARN as LOG_WARN
from os import listdir


class ServerProtocol(asyncio.Protocol):
    def __init__(self, bot: DiscordBot):
        super().__init__()
        self.bot = bot

    async def process_message(self, message: str):
        # match & case not available < Python3.10
        if message == "ping":
            self.bot.log(f"{self.str_conn} Ping received", name="discord.socket", level=LOG_DEBUG)

        elif message == "reload":
            # reload config
            self.bot.config = load_config()
            # reload all views
            reload_views()
            # unload all cogs
            await cogs_manager(
                self.bot,
                "unload",
                [
                    cog for 
                    cog in 
                    self.bot.extensions
                ]
            )
            # load all cogs (even additional ones)
            await cogs_manager(
                self.bot,
                "load",
                [
                    f"cogs.{filename[:-3]}" for
                    filename in 
                    listdir(cogs_directory) if 
                    filename.endswith(".py")
                ]
            )
            # sync commands
            await self.bot.tree.sync()

        else:
            self.bot.log(f"{self.str_conn} Unknown message received: {message}", name="discord.socket", level=LOG_WARN)

    def connection_made(self, transport: asyncio.Transport):
        self.host, self.port = transport.get_extra_info("peername")
        self.str_conn = f"({self.host}:{self.port}) :"

        self.bot.log(f"{self.str_conn} Connection made", name="discord.socket", level=LOG_DEBUG)
        self.transport = transport

    def data_received(self, data):
        message = data.decode(encoding="utf-8")
        self.bot.log(f"{self.str_conn} Data received: {message}", name="discord.socket", level=LOG_INFO)
        
        self.bot.loop.create_task(self.process_message(message))

        self.transport.write(data)
        self.bot.log(f"{self.str_conn} Answered", name="discord.socket", level=LOG_DEBUG)

        self.transport.close()
        self.bot.log(f"{self.str_conn} Connection closed", name="discord.socket", level=LOG_DEBUG)

class SocketTransport(commands.Cog, name="socket"):
    def __init__(self, bot: DiscordBot):
        self.bot = bot

    async def startup_server(self):
        self.server = await self.bot.loop.create_server(
            protocol_factory = lambda: ServerProtocol(self.bot),
            host = "127.0.0.1",
            port = 50000
        )

        async with self.server:
            await self.server.serve_forever()

    async def cog_load(self):
        self.bot.loop.create_task(self.startup_server())
        self.bot.log("Socket server started", name="discord.socket", level=LOG_DEBUG)

    async def cog_unload(self):
        self.server.close()
        self.bot.log("Socket server stopped", name="discord.socket", level=LOG_DEBUG)


async def setup(bot: DiscordBot):
    await bot.add_cog(SocketTransport(bot))
