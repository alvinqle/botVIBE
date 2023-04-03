import os

from discord.ext import commands, tasks
import discord

from youtube_helpers import YTDLSource


class DiscordBot:

    intents = discord.Intents().all()
    client = discord.Client(intents=intents)
    bot_vibe = commands.Bot(command_prefix='!', intents=intents)

    def __init__(self):
        self.api_token = os.environ['DISCORD_API_TOKEN']
        self.YTDLSource = YTDLSource()

    @bot_vibe.command(name='join', help='Tells the bot to join the voice channel')
    async def join(self, ctx):
        if not ctx.message.author.voice:
            await ctx.send(f'{ctx.message.author.name} is not connected to a voice channel.')
            return
        else:
            channel = ctx.message.author.voice.channel
        await channel.connect()

    @bot_vibe.command(name='leave', help='To make the bot leave the voice channel')
    async def leave(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_connected():
            await voice_client.disconnect()
        else:
            await ctx.send('The bot is not connected to a voice channel.')

    @bot_vibe.command(name='play_song', help='To play song')
    async def play(self, ctx, url):
        try:
            server = ctx.message.guild
            voice_channel = server.voice_client

            async with ctx.typing():
                filename = await YTDLSource.from_url(url, loop=bot_vibe.loop)
                voice_channel.play(discord.FFmpegPCMAudio(executable="ffmpeg.exe", source=filename))
            await ctx.send('**Now playing:** {}'.format(filename))
        except:
            await ctx.send("The bot is not connected to a voice channel.")

    @bot_vibe.command(name='pause', help='This command pauses the song')
    async def pause(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_playing():
            await voice_client.pause()
        else:
            await ctx.send("The bot is not playing anything at the moment.")

    @bot_vibe.command(name='resume', help='Resumes the song')
    async def resume(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_paused():
            await voice_client.resume()
        else:
            await ctx.send("The bot was not playing anything before this. Use play_song command")

    @bot_vibe.command(name='stop', help='Stops the song')
    async def stop(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_playing():
            await voice_client.stop()
        else:
            await ctx.send("The bot is not playing anything at the moment.")
