import asyncio
import discord
import youtube_dl


class YTDLSource(discord.PCMVolumeTransformer):

    youtube_dl.utils.bug_reports_message = lambda: ''

    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.ytdl_format_options = {
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
        self.ffmpeg_options = {
            'options': '-vn'
        }
        self.ytdl = youtube_dl.YoutubeDL(self.ytdl_format_options)
        self.data = data
        self.title = data.get('title')
        self.url = ""

    async def from_url(self, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        filename = data['title'] if stream else self.ytdl.prepare_filename(data)
        return filename
