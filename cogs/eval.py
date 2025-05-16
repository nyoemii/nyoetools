from types import CodeType
from typing import Any, Optional
import sys
import traceback
import resource
import logging
from multiprocessing import Process, Manager, Pipe
from datetime import datetime
import pytz

from AccessControl.ZopeGuards import get_safe_globals
from AccessControl.ImplPython import guarded_getattr as guarded_getattr_safe
from RestrictedPython import compile_restricted
from nextcord import Colour, Embed, IntegrationType, Interaction, InteractionContextType, slash_command
from nextcord.ext.commands import Bot, Cog

TIMEZONE = pytz.timezone('Europe/Amsterdam') # or your own timezone (still broken)

def memory_limit(limit_in_mb: int):
    _, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (limit_in_mb * 1024 *1024, hard))

def do_run(byte_code: CodeType, exec_namespace: dict[str, Any], ret: list[Any]):
    exec(byte_code, exec_namespace, None)
    ret.append(exec_namespace["results"])

class EvalFilter(logging.Filter):
    def filter(self, record: logging.LogRecord):
        return "Cleaning up" not in record.getMessage()

class TimeFormat(logging.Formatter):
    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None):
        dt = datetime.fromtimestamp(record.created, TIMEZONE)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat()

for handler in logging.root.handlers:
    handler.setFormatter(TimeFormat())

nextcord_logger = logging.getLogger("nextcord")
nextcord_logger.addFilter(EvalFilter())

class ExProcess(Process):
    def __init__(self, *args: Any, **kwargs: Any):
        Process.__init__(self, *args, **kwargs)
        self._pconn, self._cconn = Pipe()
        self._exception = None

    def run(self):
        try:
            Process.run(self)
            self._cconn.send(None)
        except Exception as e:
            tb = traceback.format_exc()
            self._cconn.send((e, tb))

    @property
    def exception(self):
        if self._pconn.poll():
            self._exception = self._pconn.recv()
        return self._exception

class Eval(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command(
        name="eval",
        description="evaluate Python code (sandboxed)",
        integration_types=[
            IntegrationType.user_install,
            IntegrationType.guild_install,
        ],
        contexts=[
            InteractionContextType.guild,
            InteractionContextType.bot_dm,
            InteractionContextType.private_channel,
        ]
    )
    async def evaluate(self, interaction: Interaction[Bot], *, code: str, ephemeral: bool = False) -> None:
        """A command to run restricted Python Code and return the result"""
        if not interaction.user:
            return

        trusted_trusted_users = { 353736669138255874 }

        await interaction.response.defer(ephemeral=ephemeral)

        memory_limit(1024)

        if interaction.user.id in trusted_trusted_users:
            exec_namespace: dict[str, Any] = {
                **globals(),
                **locals(),
                **{mod.__name__: mod for mod in sys.modules.values()}
            }
            realcode = "sys.stdout = io.StringIO()\n" \
                + code \
                + "\nresults = sys.stdout.getvalue(); sys.stdout = sys.__stdout__"
        else:
            exec_namespace: dict[str, Any] = get_safe_globals()
            exec_namespace.update({
                '_getattr_': guarded_getattr_safe,
                '__name__': "plxspace",
                '__metaclass__': type
            })
            realcode = code + "\nresults = printed"

        try:
            if interaction.user.id in trusted_trusted_users:
                byte_code = compile(realcode, filename="<string>", mode="exec")
            else:
                byte_code = compile_restricted(realcode, filename="<string>", mode="exec")
        except Exception as e:
            trace = traceback.format_exc()
            print(
                f"FAILED - \
User {interaction.user.name} ({interaction.user.id}) \
failed to compile {repr(code)} with Error: {trace}",
                file=sys.stderr
            )
            if isinstance(e, SyntaxError):
                msg = str(e)
            else:
                msg = getattr(e, 'message', repr(e))
            embed = Embed(
                color=Colour.red(),
                title="Error",
                description=f"`{msg}`\n-# Failed during compilation"
            )
            await interaction.send(embed=embed, ephemeral=ephemeral)
            return

        mgr = Manager()
        ret = mgr.list()
        p = ExProcess(target=do_run, args=(byte_code, exec_namespace,ret,))
        p.start()
        start_time = datetime.now(TIMEZONE)
        p.join(5)
        if p.is_alive():
            p.kill()
            p.join()

        exec_time = (datetime.now(TIMEZONE) - start_time).total_seconds()

        if p.exception:
            e = p.exception[0]
            trace = p.exception[1]
            exec_time = (datetime.now(TIMEZONE) - start_time).total_seconds()
            print(
                f"FAILED - \
User {interaction.user.name} ({interaction.user.id}) \
executed {repr(code)} \
- Executed in {exec_time:.3f}s with Error: {trace}",
                file=sys.stderr
            )
            # Send the error traceback to the channel
            embed = Embed(
                color=Colour.red(),
                title="Error",
                description=f"`{getattr(e, 'message', repr(e))}`\n-# Failed in {exec_time*1000:.1f} ms"
            )
            await interaction.send(embed=embed, ephemeral=ephemeral)
            return
        # Send the result to the channel
        result = ret[0] if len(ret) != 0 else ""
        print(
            f"SUCCESS - \
User {interaction.user.name} ({interaction.user.id}) \
executed {repr(code)} \
- Executed in {exec_time:.3f}s"
        )
        result = result.replace("`", r"\u200B`")\
              .replace("*", r"\u200B*")\
              .replace("_", r"\u200B_")
        embed = Embed(
            color=Colour.green(),
            title="Result",
            description=(f'```\n{result}\n```' if result != "" else "No output generated.")
                + f"\n-# Executed in {exec_time*1000:.1f} ms"
        )
        await interaction.send(embed=embed, ephemeral=ephemeral)
        return