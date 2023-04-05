import asyncio
import random

from discord.ext import commands
import discord
import yt_dlp as youtube_dl

from helpers.dynamodb_client import update_session

# DISCORD_API_TOKEN = os.environ['DISCORD_API_TOKEN']

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

    def __init(self, bot):
        self.bot = bot

    @commands.command(name='join', help='Commands botVIBE to join the voice channel')
    async def join(self, ctx):
        if not ctx.message.author.voice:
            await ctx.send(f'{ctx.message.author.name} is not connected to a voice channel')
            return
        else:
            channel = ctx.message.author.voice.channel
        await channel.connect()

    @commands.command(name='leave', help='Commands botVIBE to leave the channel')
    async def leave(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_connected():
            await voice_client.disconnect()
        else:
            await ctx.send('I am not connected to a voice channel. Connect me to your channel with the !join command.')


class AudioCommands(commands.Cog, name='Audio Commands'):

    def __init__(self, bot):
        self.bot = bot
        self.general_commands = GeneralCommands()

    @commands.command(name='play', help='Takes in a url to a video and plays the audio')
    @commands.has_any_role('DJ')
    async def play(self, ctx, url):
        try:
            voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
            if not (voice_client and voice_client.is_connected()):
                await self.general_commands.join(ctx)
            server = ctx.message.guild
            voice_channel = server.voice_client
            async with ctx.typing():
                url, title = await YTDLSource.from_url(url, loop=bot_vibe.loop)
                voice_channel.play(discord.FFmpegPCMAudio(source=url, executable='ffmpeg.exe', **ffmpeg_options))
            await ctx.send(f'**Now playing:** {title}')
        except Exception as e:
            await ctx.send(str(e))

    @commands.command(name='pause', help='Pauses any currently playing audio')
    async def pause(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_playing():
            await voice_client.pause()
        else:
            await ctx.send('I am not playing anything at the moment. Play a song with the !play [url] command.')

    @commands.command(name='resume', help='Resumes any paused audio')
    async def resume(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_paused():
            await voice_client.resume()
        else:
            await ctx.send('I was not playing anything before this. Play a song with the !play [url] command.')

    @commands.command(name='stop', help='Stops any currently playing or paused audio')
    async def stop(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_playing():
            await voice_client.stop()
        else:
            await ctx.send('I am not playing anything at the moment. Play a song with the !play [url] command.')


class MemberCommands(commands.Cog, name='Member Commands'):

    def __init__(self, bot):
        self.bot = bot
        self.general_commands = GeneralCommands()

    @bot_vibe.command(name='movedown', help='Moves tagged users down one voice channel')
    @commands.has_any_role('admin')
    async def movedown(self, ctx, *, msg):
        channel = ctx.message.author.voice.channel
        channel_index = channel.guild.voice_channels.index(channel)
        if channel_index == len(channel.guild.voice_channels) - 1:
            await ctx.send(f'Cannot move users up a channel from the top channel')
        else:
            users = msg.replace('!', '') \
                .replace('<', '') \
                .replace('@', '') \
                .replace('>', '').split(' ')
            for user in users:
                member = ctx.guild.get_member(int(user))
                current_channel_index = ctx.guild.voice_channels.index(member.voice.channel)
                await member.move_to(channel.guild.voice_channels[current_channel_index + 1])

    @bot_vibe.command(name='movehere', help='Moves tagged users to the channel the author is connected to')
    @commands.has_any_role('admin')
    async def movehere(self, ctx, *, msg):
        channel = ctx.message.author.voice.channel
        channel_index = channel.guild.voice_channels.index(channel)
        if channel_index == len(channel.guild.voice_channels) - 1:
            await ctx.send(f'Cannot move users up a channel from the top channel')
        else:
            users = msg.replace('!', '') \
                .replace('<', '') \
                .replace('@', '') \
                .replace('>', '').split(' ')
            for user in users:
                member = ctx.guild.get_member(int(user))
                await member.move_to(channel)

    @bot_vibe.command(name='moveto', help='Moves tagged users up one voice channel')
    @commands.has_any_role('admin')
    async def moveto(self, ctx, *, msg):
        new_channel, users = msg.split('"')[1], msg.split('"')[2]
        users = users.replace(' ', '') \
            .replace('!', '') \
            .replace('<', '') \
            .replace('@', '') \
            .replace('>', '').split(' ')
        for user in users:
            member = ctx.guild.get_member(int(user))
            new_channel = discord.utils.get(ctx.guild.voice_channels, name=new_channel)
            await member.move_to(new_channel)

    @bot_vibe.command(name='moveup', help='Moves tagged users up one voice channel')
    @commands.has_any_role('admin')
    async def moveup(self, ctx, *, msg):
        channel = ctx.message.author.voice.channel
        channel_index = channel.guild.voice_channels.index(channel)
        if channel_index == 0:
            await ctx.send(f'Cannot move users up a channel from the top channel')
        else:
            users = msg.replace('!', '') \
                .replace('<', '') \
                .replace('@', '') \
                .replace('>', '').split(' ')
            for user in users:
                member = ctx.guild.get_member(int(user))
                current_channel_index = ctx.guild.voice_channels.index(member.voice.channel)
                await member.move_to(channel.guild.voice_channels[current_channel_index - 1])


class MiscellaneousCommands(commands.Cog, name='Miscellaneous Commands'):

    def __init__(self, bot):
        self.bot = bot
        self.general_commands = GeneralCommands()

    @commands.command(name='flip', help='Flips a coin and returns the result')
    async def flip(self, ctx, number=1):
        if number not in {1, 3, 5, 7, 9}:
            await ctx.send('Please input an odd number between 0 and 10')
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
            await asyncio.sleep(2)
            if heads > tails:
                await ctx.send(f'Heads wins! {heads} to {tails}')
            else:
                await ctx.send(f'Tails wins! {tails} to {heads}')


@bot_vibe.command(name='ping', help='pong')
async def ping(ctx):
    await ctx.send(f'pong | {round(bot_vibe.latency) * 1000} ms')


@bot_vibe.command(name='shutdown', help='Shuts down the bot entirely - use /botvibe to restart the bot')
async def shutdown(ctx):
    update_session(bot_name='botVIBE', active=False)
    exit()


async def setup_bot():
    await bot_vibe.add_cog(GeneralCommands(bot_vibe))
    await bot_vibe.add_cog(AudioCommands(bot_vibe))
    await bot_vibe.add_cog(MiscellaneousCommands(bot_vibe))


def run_bot():
    bot_vibe.run('ODAwNjMxMDk3ODY4MTU2OTQ4.GhdafG.oQmqj_1RsrpQhJ_12QG0z3FiPidsfOjlHdWLlo')
