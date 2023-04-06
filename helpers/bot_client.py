import asyncio
import json
import os
import random

from discord.ext import commands
import discord
import yt_dlp as youtube_dl

from helpers.dynamodb_client import update_session

DISCORD_API_TOKEN = os.environ['DISCORD_API_TOKEN']

intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot_vibe = commands.Bot(command_prefix='!', intents=intents)

youtube_dl.utils.bug_reports_message = lambda: ''
ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}
ffmpeg_options = {
    'options': '-vn'
}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = ''

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        url, title = data['url'], data['title']
        return url, title


class GeneralCommands(commands.Cog, name='General Commands'):

    @commands.command(name='join', help='Commands botVIBE to join the voice channel')
    async def join(self, ctx):
        try:
            if not ctx.message.author.voice:
                await ctx.send(f'You are not connected to a voice channel.')
                return
            else:
                channel = ctx.message.author.voice.channel
            await channel.connect()
        except Exception as e:
            await ctx.send(str(e))

    @commands.command(name='leave', help='Commands botVIBE to leave the channel')
    async def leave(self, ctx):
        try:
            voice_client = ctx.message.guild.voice_client
            if voice_client.is_connected():
                await voice_client.disconnect()
            else:
                await ctx.send('I am not connected to a voice channel. Connect me to your channel with !join.')
        except Exception as e:
            await ctx.send(str(e))


class AudioCommands(commands.Cog, name='Audio Commands'):

    def __init__(self):
        self.general_commands = GeneralCommands()

    @commands.command(name='play', help='Takes in a url to a video and plays the audio')
    @commands.has_any_role('DJ')
    async def play(self, ctx, url):
        try:
            voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
            if not (voice_client and voice_client.is_connected()):
                await self.general_commands.join(self, ctx)
            server = ctx.message.guild
            voice_channel = server.voice_client
            async with ctx.typing():
                url, title = await YTDLSource.from_url(url, loop=bot_vibe.loop)
                voice_channel.play(discord.FFmpegPCMAudio(source=url, executable='ffmpeg.exe', **ffmpeg_options))
            await ctx.send(f'**Now playing:** {title}')
            while True:
                await asyncio.sleep(1)
                if not voice_channel.is_playing():
                    await voice_channel.disconnect()
                    break
        except Exception as e:
            await ctx.send(str(e))

    @commands.command(name='pause', help='Pauses any currently playing audio')
    async def pause(self, ctx):
        try:
            voice_client = ctx.message.guild.voice_client
            if voice_client.is_playing():
                await voice_client.pause()
            else:
                await ctx.send('I am not playing anything at the moment. Play a song with !play [url].')
        except Exception as e:
            await ctx.send(str(e))

    @commands.command(name='resume', help='Resumes any paused audio')
    async def resume(self, ctx):
        try:
            voice_client = ctx.message.guild.voice_client
            if voice_client.is_paused():
                await voice_client.resume()
            else:
                await ctx.send('I am not playing anything at the moment. Play a song with !play [url].')
        except Exception as e:
            await ctx.send(str(e))

    @commands.command(name='stop', help='Stops any currently playing or paused audio')
    async def stop(self, ctx):
        try:
            voice_client = ctx.message.guild.voice_client
            if voice_client.is_playing():
                await voice_client.stop()
            else:
                await ctx.send('I am not playing anything at the moment. Play a song with !play [url].')
        except Exception as e:
            await ctx.send(str(e))


class MemberCommands(commands.Cog, name='Member Commands'):

    @commands.command(name='movedown', help='Moves tagged users down one voice channel')
    @commands.has_any_role('admin')
    async def movedown(self, ctx, *, msg):
        try:
            users = msg.replace('!', '') \
                .replace('<', '') \
                .replace('@', '') \
                .replace('>', '').split(' ')
            for user in users:
                member = ctx.guild.get_member(int(user))
                if member.voice is None:
                    await ctx.send(f'{member.name} is not in any voice channel.')
                    continue
                current_channel_index = ctx.guild.voice_channels.index(member.voice.channel)
                if current_channel_index == len(ctx.guild.voice_channels) - 1:
                    await ctx.send(f'Cannot move {member.name} down a channel from the bottom channel.')
                    continue
                await member.move_to(ctx.guild.voice_channels[current_channel_index + 1])
        except Exception as e:
            await ctx.send(f'ERROR: {str(e)}')

    @commands.command(name='movehere', help='Moves tagged users to the channel the author is connected to')
    @commands.has_any_role('admin')
    async def movehere(self, ctx, *, msg):
        try:
            if not ctx.message.author.voice:
                await ctx.send(f'{ctx.message.author.name} is not connected to a voice channel.')
                return
            current_channel = ctx.message.author.voice.channel
            prev_channel_name = None
            if '"' in msg:
                prev_channel_name = msg.split('"')[1]
            else:
                users = msg.replace('!', '') \
                    .replace('<', '') \
                    .replace('@', '') \
                    .replace('>', '').split(' ')
            if not prev_channel_name:
                for user in users:
                    member = ctx.guild.get_member(int(user))
                    if member.voice is None:
                        await ctx.send(f'{member.name} is not in any voice channel.')
                        continue
                    await member.move_to(current_channel)
            else:
                if prev_channel_name not in _list_voice_channels(ctx):
                    await ctx.send(f'{prev_channel_name} is not a valid voice channel.')
                    return
                prev_channel = discord.utils.get(ctx.guild.voice_channels, name=prev_channel_name)
                for member in prev_channel.members:
                    if member.voice is None:
                        await ctx.send(f'{member.name} is not in any voice channel.')
                        continue
                    await member.move_to(current_channel)
        except Exception as e:
            await ctx.send(f'ERROR: {str(e)}\nUsage: !movehere "CHANNEL_NAME" or !movehere @USER_NAME')

    @commands.command(name='moveto', help='Moves tagged users up one voice channel')
    @commands.has_any_role('admin')
    async def moveto(self, ctx, *, msg):
        try:
            new_channel_name, users = msg.split('"')[1], msg.split('"')[2]
            if new_channel_name not in _list_voice_channels(ctx):
                await ctx.send(f'{new_channel_name} is not a valid voice channel.')
                return
            new_channel = discord.utils.get(ctx.guild.voice_channels, name=new_channel_name)
            prev_channel_name = None
            if users == ' ':
                prev_channel_name = msg.split('"')[3]
            else:
                users = users.lstrip(' ') \
                    .replace('!', '') \
                    .replace('<', '') \
                    .replace('@', '') \
                    .replace('>', '').split(' ')
            if not prev_channel_name:
                for user in users:
                    member = ctx.guild.get_member(int(user))
                    if member.voice is None:
                        await ctx.send(f'{member.name} is not online.')
                        continue
                    await member.move_to(new_channel)
            else:
                if prev_channel_name not in _list_voice_channels(ctx):
                    await ctx.send(f'{prev_channel_name} is not a valid voice channel.')
                    return
                prev_channel = discord.utils.get(ctx.guild.voice_channels, name=prev_channel_name)
                for member in prev_channel.members:
                    if member.voice is None:
                        await ctx.send(f'{member.name} is not in any voice channel.')
                        continue
                    await member.move_to(new_channel)
        except Exception as e:
            await ctx.send(f'ERROR: {str(e)}\nUsage: !moveto "CHANNEL_NAME" @USER_NAME')

    @commands.command(name='moveup', help='Moves tagged users up one voice channel')
    @commands.has_any_role('admin')
    async def moveup(self, ctx, *, msg):
        try:
            users = msg.replace('!', '') \
                .replace('<', '') \
                .replace('@', '') \
                .replace('>', '').split(' ')
            for user in users:
                member = ctx.guild.get_member(int(user))
                if member.voice is None:
                    await ctx.send(f'{member.name} is not in any voice channel.')
                    continue
                current_channel_index = ctx.guild.voice_channels.index(member.voice.channel)
                if current_channel_index == 0:
                    await ctx.send(f'Cannot move {member.name} up a channel from the top channel.')
                    continue
                await member.move_to(ctx.guild.voice_channels[current_channel_index - 1])
        except Exception as e:
            await ctx.send(f'ERROR{str(e)}')


class MiscellaneousCommands(commands.Cog, name='Miscellaneous Commands'):

    def __init__(self):
        self.audio_commands = AudioCommands()
        self.general_commands = GeneralCommands()

    @commands.command(name='flip', help='Flips a coin and returns the result')
    async def flip(self, ctx, number=1):
        try:
            if number not in {1, 3, 5, 7, 9}:
                await ctx.send('Please input an odd number between 0 and 10.')
            else:
                await ctx.send(f'Flipping a coin {number} time(s)...')
                heads, tails = 0, 0
                for i in range(number):
                    result = random.randint(0, 1)
                    if result == 0:
                        heads += 1
                        if heads > (number // 2):
                            break
                    else:
                        tails += 1
                        if tails > (number // 2):
                            break
                await asyncio.sleep(1)
                if heads > tails:
                    await ctx.send(f'Heads wins! {heads} to {tails}')
                else:
                    await ctx.send(f'Tails wins! {tails} to {heads}')
        except Exception as e:
            await ctx.send(str(e))

    @commands.command(name='pick', help='Picks a random game to play based on the amount of players in a channel')
    async def pick(self, ctx):
        try:
            current_channel = ctx.message.author.voice.channel
            player_count = len(current_channel.members)
            with open('./config/games.json') as games_file:
                games_list = json.load(games_file)
            potential_games = []
            for max_player_count, games in games_list['max_player_count'].items():
                if player_count < int(max_player_count):
                    potential_games.extend(games)
            await asyncio.sleep(1)
            await ctx.send(f'Why not play {potential_games[random.randint(0, len(potential_games) - 1)]}?')
        except Exception as e:
            await ctx.send(f'ERROR: {str(e)}')

    @commands.command(name='womp')
    async def womp(self, ctx):
        try:
            await self.general_commands.join(self, ctx)
            await self.audio_commands.play(self, ctx, url='https://www.youtube.com/watch?v=CQeezCdF4mk')
        except Exception as e:
            await ctx.send(str(e))


@bot_vibe.command(name='ping', help='pong')
async def ping(ctx):
    try:
        await ctx.send(f'pong | {round(bot_vibe.latency) * 1000} ms')
    except Exception as e:
        await ctx.send(str(e))


@bot_vibe.command(name='shutdown', help='Shuts down the bot entirely - use /botvibe to restart the bot')
async def shutdown(ctx):
    try:
        update_session(bot_name='botVIBE', active=False)
        exit()
    except Exception as e:
        await ctx.send(str(e))
        exit()


def _list_voice_channels(ctx):
    return [channel.name for channel in ctx.guild.voice_channels]


async def setup_bot():
    await bot_vibe.add_cog(GeneralCommands())
    await bot_vibe.add_cog(AudioCommands())
    await bot_vibe.add_cog(MemberCommands())
    await bot_vibe.add_cog(MiscellaneousCommands())


def run_bot():
    bot_vibe.run(DISCORD_API_TOKEN)
