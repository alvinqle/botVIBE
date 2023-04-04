import asyncio
import json
import os

from discord.ext import commands, tasks
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import discord
import yt_dlp as youtube_dl

DISCORD_API_TOKEN = os.environ['DISCORD_API_TOKEN']
DISCORD_PUBLIC_KEY = os.environ['DISCORD_PUBLIC_KEY']

intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot_vibe = commands.Bot(command_prefix='!', intents=intents)

youtube_dl.utils.bug_reports_message = lambda: ''
ytdl_format_options = {
    'outtmpl': '/tmp/%(title)s-%(id)s.%(ext)s',
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


def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        signature = event['headers']['x-signature-ed25519']
        timestamp = event['headers']['x-signature-timestamp']

        # validate the interaction
        verify_key = VerifyKey(bytes.fromhex(DISCORD_PUBLIC_KEY))
        message = timestamp + json.dumps(body, separators=(',', ':'))

        try:
            verify_key.verify(message.encode(), signature=bytes.fromhex(signature))
        except BadSignatureError:
            return {
                'statusCode': 401,
                'body': json.dumps('invalid request signature')
            }

        # handle the interaction
        t = body['type']
        if t == 1:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'type': 1
                })
            }
        elif t == 2:
            return command_handler(body)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps('unhandled request type')
            }
    except:
        raise


def command_handler(body):
    command = body['data']['name']

    if command == 'botvibe':
        bot_vibe.run(DISCORD_API_TOKEN)
    else:
        return {
            'statusCode': 400,
            'body': json.dumps('unhandled command')
        }


class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = ""

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        url, title = data['url'], data['title']
        return url, title


@bot_vibe.command(name='play', help='To play song')
async def play(ctx, url):
    try:
        server = ctx.message.guild
        voice_channel = server.voice_client

        async with ctx.typing():
            url, title = await YTDLSource.from_url(url, loop=bot_vibe.loop)
            voice_channel.play(discord.FFmpegPCMAudio(source=url, **ffmpeg_options))
        await ctx.send(f'**Now playing:** {title}')
    except Exception as e:
        await ctx.send(str(e))


@bot_vibe.command(name='join', help='Tells the bot to join the voice channel')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send(f'{ctx.message.author.name} is not connected to a voice channel')
        return
    else:
        channel = ctx.message.author.voice.channel
    await channel.connect()


@bot_vibe.command(name='pause', help='This command pauses the song')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.pause()
    else:
        await ctx.send('I am not playing anything at the moment. Play a song with the !play command.')


@bot_vibe.command(name='resume', help='Resumes the song')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        await voice_client.resume()
    else:
        await ctx.send('I was not playing anything before this. Play a song with the !play command.')


@bot_vibe.command(name='leave', help='To make the bot leave the voice channel')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
    else:
        await ctx.send('I am not connected to a voice channel. Connect me to your channel with the !join command.')


@bot_vibe.command(name='stop', help='Stops the song')
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.stop()
    else:
        await ctx.send('I am not playing anything at the moment. Play a song with the !play command.')
