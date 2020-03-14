"""
Cog implementing the void
Part of the void.
"""

import logging
from typing import TYPE_CHECKING, Optional, Dict, List, Union, Tuple, NamedTuple, Type, Any

import discord
from discord.ext import commands

import eCommands
import db

from utils.uiElements import BoolPage
from utils.misc import get_webhook

if TYPE_CHECKING:
    from bot import VBot

log = logging.getLogger(__name__)


class Void(commands.Cog):

    def __init__(self, bot: 'VBot'):
        self.bot = bot
    #     self.void = {}
    #     self.initialized = False
    #
    # await def init_void_cache(self):
    #     voids = await db.get_all_void_ch(self.bot.db_pool)
    #
    #     for void in voids:

    # region set void channels Command

    # ----- add/remove void channels Commands ----- #
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    @eCommands.group(name="void_ch", aliases=["void_channel", "vc"], brief="Add, Remove, List and Configure void channels",
                     #description="Sets/unsets/shows the default logging channel.",  # , usage='<command> [channel]'
                     examples=['list', "add #void-channel", "add 123456789123456789", 'remove #void-channel', 'time #vent 2.5']
                     )
    async def void_ch_conf(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(self.void_ch_conf)

    @void_ch_conf.command(name="add", brief="Add a new void channel",
                          examples=["#thevoid", "123456789123456789"])
    async def add_void_ch(self, ctx: commands.Context, channel: discord.TextChannel):
        ch_perm: discord.Permissions = channel.guild.me.permissions_in(channel)
        if ch_perm.manage_messages and ch_perm.read_messages:
            await db.add_void_ch(self.bot.db_pool, ctx.guild.id, channel.id, enabled=True, delete_after=5)
            embed = discord.Embed(color=0x000000,
                                  description=f"<#{channel.id}> is now a void channel and has been enabled.\n"
                                              f"All messages sent in that channel will now be deleted after 5 seconds.")
            await ctx.send(embed=embed)
        else:
            msg = f"Can not add <#{channel.id}> to the void channels.\n" \
                  f"`void` is missing the following critical permissions in <#{channel.id}> which would prevent proper operation:\n"
            if not ch_perm.manage_messages:
                msg += "**Manage Messages Permission**\n"
            if not ch_perm.read_messages:
                msg += "**Read Messages Permission**\n"
            msg += "\nPlease fix the permissions and try again or choose a different channel."
            embed = discord.Embed(color=0x000000, description=msg)
            await ctx.send(embed=embed)


    @void_ch_conf.command(name="remove", brief="Removes a void channel",
                          examples=["#screammmm", "123456789123456789"])
    async def remove_void_ch(self, ctx: commands.Context, channel: discord.TextChannel):
        await db.remove_void_ch(self.bot.db_pool, ctx.guild.id, channel.id)
        embed = discord.Embed(color=0x000000,
                              description=f"<#{channel.id}> is no longer configured as a void channel\n")
        await ctx.send(embed=embed)


    @void_ch_conf.command(name="list", brief="Lists the configured void channels")
    async def list_void_ch(self, ctx: commands.Context):

        void_channels = await db.get_void_channels_for_guild(self.bot.db_pool, ctx.guild.id)
        if len(void_channels) > 0:
            msg = ["The following channels are currently configured as void channels:"]
            for void_ch in void_channels:
                enabled_txt = "enabled" if void_ch.enabled else "Disabled"
                msg.append(f"<#{void_ch.channel_id}> ({enabled_txt})")
        else:
            msg = ["There are currently no channels configured as void channels.\n"]
            embed = discord.Embed(title="Configured Void Channels",
                                  description="\n".join(msg),
                                  color=0x000000)
            await ctx.send(embed=embed)

    @void_ch_conf.command(name="enable", brief="Enables a void channel",
                          examples=["#screammmm", "123456789123456789"])
    async def enable_void_ch(self, ctx: commands.Context, channel: discord.TextChannel):
        existing_void_ch_settings = await db.get_void_channel(self.bot.db_pool, channel.id)
        if existing_void_ch_settings is not None:
            await db.toggle_void_ch(self.bot.db_pool, ctx.guild.id, channel.id, True)
            embed = discord.Embed(color=0x000000,
                                  description=f"<#{channel.id}> is now enabled. All messages sent in that channel will now be deleted after {existing_void_ch_settings.delete_after} seconds..\n")
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(color=0x000000,
                                  description=f"\N{WARNING SIGN} <#{channel.id}> has not yet been configured as a void channel!\n")
            await ctx.send(embed=embed)

    @void_ch_conf.command(name="disable", brief="Disables a void channel",
                          examples=["#screammmm", "123456789123456789"])
    async def disable_void_ch(self, ctx: commands.Context, channel: discord.TextChannel):
        existing_void_ch_settings = await db.get_void_channel(self.bot.db_pool, channel.id)

        if existing_void_ch_settings is not None:
            await db.toggle_void_ch(self.bot.db_pool, ctx.guild.id, channel.id, False)
            embed = discord.Embed(color=0x000000,
                                  description=f"<#{channel.id}> is now disabled. Messages will no longer be deleted.\n")
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(color=0x000000,
                                  description=f"\N{WARNING SIGN} <#{channel.id}> has not yet been configured as a void channel!\n")
            await ctx.send(embed=embed)

    @void_ch_conf.command(name="time", brief="Sets how long until messages are deleted from a channel",
                          examples=["#screammmm 1.4", "123456789123456789 6"])
    async def time_void_ch(self, ctx: commands.Context, channel: discord.TextChannel, seconds: float):
        existing_void_ch_settings = await db.get_void_channel(self.bot.db_pool, channel.id)
        if existing_void_ch_settings is not None:
            if seconds >= 0:
                await db.set_void_delete_time(self.bot.db_pool, ctx.guild.id, channel.id, delete_after=seconds)
                time_msg = "immediately" if seconds == 0 else f"after {seconds} seconds"
                embed = discord.Embed(color=0x000000,
                                      description=f"Messages in <#{channel.id}> will now be deleted {time_msg}.\n")
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(color=0x000000,
                                      description=f"The time entered must be positive!\n")
                await ctx.send(embed=embed)
        else:
            embed = discord.Embed(color=0x000000,
                                  description=f"\N{WARNING SIGN} <#{channel.id}> has not yet been configured as a void channel!\n")
            await ctx.send(embed=embed)

    # endregion

    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    @eCommands.group(name="proxy", aliases=["p"],
                     brief="Sends a proxies message that won't be deleted.",
                     examples=['Imagine a witty message here']
                     )
    async def proxy(self, ctx: commands.Context, *, message: str):
        ch: discord.TextChannel = ctx.channel
        author: Union[discord.Member, discord.User] = ctx.author
        try:
            webhook: discord.Webhook = await get_webhook(self.bot, ch)
        except discord.Forbidden:
            embed = discord.Embed(color=0x000000,
                                  title="`void` proxy",
                                  description=f"\N{WARNING SIGN} The proxy command requires that `void` has the **Manage Webhooks** permission.\n"
                                              f"\nThis message will be sucked into the void in 20 seconds.")
            await ctx.send(embed=embed, delete_after=20)
            return

        avatar = author.avatar_url_as(static_format="png")
        clean_content = discord.utils.escape_mentions(message)
        await webhook.send(content=clean_content, username=author.display_name, avatar_url=avatar)

    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    @eCommands.group(name="purge",
                     brief="Purges a channel of 'n' messages.",
                     examples=['20'],
                     usage="<Number Of Messages>"
                     )
    async def purge(self, ctx: commands.Context, num: int):
        ch: discord.TextChannel = ctx.channel

        embed = discord.Embed(title="`void` purge", description=f"Are you sure you want to delete the last {num} messages?")
        confirmation= BoolPage(embed=embed)
        yes = await confirmation.run(ctx)
        if yes:
            try:
                await ch.purge(limit=num)
            except discord.Forbidden:
                embed = discord.Embed(color=0x000000,
                                      description=f"\N{WARNING SIGN} Could not purge messages! The purge command requires that `void` has the **Manage Messages** and the **Read Message History** permissions.\n"
                                                  f"\nThis message will be sucked into the void in 20 seconds.")
                await ctx.send(embed=embed, delete_after=20)
                return


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handles the 'on_message' event."""

        if self.bot.user.id == message.author.id:
            if len(message.embeds) > 0 and message.embeds[0].title is not None:
                if message.embeds[0].title == '`void` purge' or message.embeds[0].title == "`void` proxy":
                    return  # Don't void some of our messages. We can handle that.

            # check if this is a void channel
            void_ch = await db.get_void_channel(self.bot.db_pool, message.channel.id)
            if void_ch is not None and void_ch.enabled:

                # check if it's a webhook msg from void
                if message.webhook_id is not None:
                    log.info(f"{message.webhook_id}")
                    if message.channel.id in self.bot.webhook_cache.keys() and self.bot.webhook_cache[message.channel.id].id == message.webhook_id:
                        return  # It's a proxy msg from void. Don't delete.

                await message.delete(delay=void_ch.delete_after)


def setup(bot):
    bot.add_cog(Void(bot))
