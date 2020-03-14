"""


"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, Dict, List, Union, Tuple, NamedTuple, Callable, Any

import discord
from discord.ext import commands



class DiscordPermissionsError(Exception):
    pass


class CannotAddReactions(DiscordPermissionsError):
    def __init__(self):
        super().__init__(f"Insufficient permissions to add reactions to user interface!\n"
                         f"Please have an admin add the **Add Reactions** and **Read Message History** permissions to this bot and make sure that the channel you are using commands in is configured to allow those permissions as well.")


class CannotEmbedLinks(DiscordPermissionsError):
    def __init__(self):
        super().__init__('Bot does not have embed links permission in this channel.')


class CannotSendMessages(DiscordPermissionsError):
    def __init__(self):
        super().__init__('Bot cannot send messages in this channel.')


class CannotAddExtenalReactions(DiscordPermissionsError):
    def __init__(self):
        super().__init__(f"Gabby Gums is missing the **Use External Emojis** Permission!\n"
                         f"Please have an admin add the **Use External Emojis** permissions to this bot and make sure that the channel you are using commands in is configured to allow External Emojis as well.")



async def do_nothing(*args, **kwargs):
    pass


@dataclass
class PageResponse:
    """Data Storage class for returning the user response (if any) and the UI Message(es) that the Page sent out."""
    response: Optional[Any]
    ui_message: Optional[discord.Message]
    # user_messages: List[discord.Message] = field(default_factory=[])

    def __str__(self):
        return str(self.content())

    def content(self):
        if isinstance(self.response, str):
            return self.response
        elif isinstance(self.response, discord.Message):
            return self.response.content
        else:
            return self.response

    def c(self):
        return self.content()


class Page:
    """
    An interactive form that can be interacted with in a variety of ways including Boolean reaction, string input, non-interactive response message, soon to be more.
    Calls a Callback with the channel and response data to enable further response and appropriate handling of the data.
    """
    LOG = logging.getLogger("GGBot.Page")

    def __init__(self, page_type: str, name: Optional[str] = None, body: Optional[str] = None,
                 callback: Callable = do_nothing, additional: str = None, embed: Optional[discord.Embed] = None, previous_msg: Optional[Union[discord.Message, PageResponse]] = None, timeout: int = 120.0):

        self.name = name
        self.body = body
        self.additional = additional
        self.embed = embed
        self.timeout = timeout

        self.page_type = page_type.lower()
        self.callback = callback
        self.prev = previous_msg.ui_message if isinstance(previous_msg, PageResponse) else previous_msg

        self.response = None
        self.page_message: Optional[discord.Message] = None
        self.user_message: Optional[discord.Message] = None

    async def run(self, ctx: commands.Context):
        pass

    def construct_std_page_msg(self) -> str:
        page_msg = ""
        if self.name is not None:
            page_msg += "**{}**\n".format(self.name)

        if self.body is not None:
            page_msg += "{}\n".format(self.body)

        if self.additional is not None:
            page_msg += "{}\n".format(self.additional)

        # self.page_message = page_message
        return page_msg

    @staticmethod
    async def cancel(ctx, self):
        await self.remove()
        await ctx.send("Canceled!")

    async def remove(self, user: bool = True, page: bool = True):

        # if self.previous is not None:
        #     await self.previous.remove(user, page)

        try:
            if user and self.user_message is not None:
                await self.user_message.delete(delay=1)
        except Exception:
            pass

        try:
            if page and self.page_message is not None:
                await self.page_message.delete(delay=1)
        except Exception:
            pass


class BoolPage(Page):

    def __init__(self, name: Optional[str] = None, body: Optional[str] = None,
                 callback: Callable = do_nothing, additional: str = None, embed: Optional[discord.Embed] = None, previous_msg: Optional[Union[discord.Message, PageResponse]] = None, timeout: int = 120.0):
        """
        Callback signature: page: reactMenu.Page, _client: commands.Bot, ctx: commands.Context, response: bool
        """
        self.ctx = None
        self.match = None
        self.canceled = False

        super().__init__(page_type="n/a", name=name, body=body, callback=callback, additional=additional, embed=embed, previous_msg=previous_msg, timeout=timeout)

    async def run(self, ctx: commands.Context):
        """
        Callback signature: page: reactMenu.Page, _client: commands.Bot, ctx: commands.Context, response: bool
        """
        self.ctx = ctx
        channel: discord.TextChannel = ctx.channel
        author: discord.Member = ctx.author
        message: discord.Message = ctx.message

        if self.embed is None:
            self.page_message = await channel.send(self.construct_std_page_msg())
        else:
            self.page_message = await channel.send(self.construct_std_page_msg(), embed=self.embed)

        try:
            await self.page_message.add_reaction("✅")
            await self.page_message.add_reaction("❌")
        except discord.Forbidden as e:
            await ctx.send(
                f"CRITICAL ERROR!!! \n{ctx.guild.me.name} does not have the `Add Reactions` permissions!. Please have an Admin fix this issue and try again.")
            raise e


        def react_check(_reaction: discord.Reaction, _user):
            self.LOG.info("Checking Reaction: Reacted Message: {}, orig message: {}".format(_reaction.message.id,
                                                                                            self.page_message.id))

            return _user == ctx.author and (str(_reaction.emoji) == '✅' or str(_reaction.emoji) == '❌')


        try:
            reaction, react_user = await self.ctx.bot.wait_for('reaction_add', timeout=self.timeout, check=react_check)
            if str(reaction.emoji) == '✅':
                self.response = True
                await self.remove()
                await self.callback(self, self.ctx.bot, ctx, True)
                return True
            elif str(reaction.emoji) == '❌':
                self.response = False
                await self.remove()
                await self.callback(self, self.ctx.bot, ctx, False)
                return False

        except asyncio.TimeoutError:
            await self.remove()
            return None
