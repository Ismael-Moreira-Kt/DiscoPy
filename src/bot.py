import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import yt_dlp as youtube_dl
import asyncio



load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
VOICE_CHANNEL_ID = int(os.getenv('VOICE_CHANNEL_ID'))
TEXT_CHANNEL_ID = int(os.getenv('TEXT_CHANNEL_ID'))



intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True



bot = commands.Bot(command_prefix='!', intents=intents)
song_queue = []
is_playing = False
current_song = None



ytdl_opts = {
    'format': 'bestaudio/best',
    'noplaylist': True,
}



def search_youtube(query):
    ytdl = youtube_dl.YoutubeDL({'format': 'bestaudio/best', 'noplaylist': True})
    info = ytdl.extract_info(f"ytsearch:{query}", download=False)
    return info['entries'][0]['url']



def get_playlist(url):
    ytdl = youtube_dl.YoutubeDL({'format': 'bestaudio/best'})
    info = ytdl.extract_info(url, download=False)
    return [entry['url'] for entry in info['entries']]



@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    
    if VOICE_CHANNEL_ID:
        channel = bot.get_channel(VOICE_CHANNEL_ID)
        if channel and isinstance(channel, discord.VoiceChannel):
            await channel.connect()
            print(f'Connected to voice channel: {channel.name}')
        else:
            print(f'Invalid voice channel ID: {VOICE_CHANNEL_ID}')
    else:
        print('No voice channel ID provided.')

    if TEXT_CHANNEL_ID:
        text_channel = bot.get_channel(TEXT_CHANNEL_ID)
        if text_channel and isinstance(text_channel, discord.TextChannel):
            await text_channel.send("Bot is online and ready to play music.")
            print(f'Connected to text channel: {text_channel.name}')
        else:
            print(f'Invalid text channel ID: {TEXT_CHANNEL_ID}')
    else:
        print('No text channel ID provided.')



async def play_next(ctx, voice_client):
    global is_playing, current_song
    if len(song_queue) > 0:
        is_playing = True
        current_song = song_queue.pop(0)
        await play_url(ctx, voice_client, current_song)
    else:
        is_playing = False
        current_song = None



@bot.command()
async def play(ctx, *, query: str):
    global song_queue, is_playing

    if ctx.author.voice is None:
        await ctx.send("You need to be in a voice channel to use this command.")
        return

    channel = ctx.author.voice.channel
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_client is None:
        voice_client = await channel.connect()

    if 'http' in query:
        url = query
    else:
        url = search_youtube(query)

    song_queue.append(url)

    if not is_playing:
        await play_next(ctx, voice_client)



async def play_url(ctx, voice_client, url):
    global current_song
    ytdl = youtube_dl.YoutubeDL(ytdl_opts)
    info = ytdl.extract_info(url, download=False)
    url2 = info['formats'][0]['url']

    ffmpeg_opts = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    voice_client.stop()
    voice_client.play(discord.FFmpegPCMAudio(url2, **ffmpeg_opts), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx, voice_client), bot.loop))

    await ctx.send(f"Now playing: {info['title']}")



@bot.command()
async def playlist(ctx, *, url: str):
    if ctx.author.voice is None:
        await ctx.send("You need to be in a voice channel to use this command.")
        return

    channel = ctx.author.voice.channel
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice_client is None:
        voice_client = await channel.connect()

    if 'playlist' in url:
        urls = get_playlist(url)
        await play_playlist(ctx, voice_client, urls)
    else:
        await ctx.send("The provided URL is not a valid playlist.")



async def play_playlist(ctx, voice_client, urls):
    for url in urls:
        ytdl = youtube_dl.YoutubeDL(ytdl_opts)
        info = ytdl.extract_info(url, download=False)
        url2 = info['formats'][0]['url']

        ffmpeg_opts = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn',
        }

        voice_client.stop()
        voice_client.play(discord.FFmpegPCMAudio(url2, **ffmpeg_opts))

        await ctx.send(f"Now playing: {info['title']}")

        while voice_client.is_playing():
            await asyncio.sleep(1)



@bot.command()
async def stop(ctx):
    if ctx.voice_client is None:
        await ctx.send("I am not in a voice channel.")
        return

    await ctx.voice_client.disconnect()
    await ctx.send("Stopped and disconnected.")



@bot.command()
async def pause(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Music paused.")
    else:
        await ctx.send("No music is currently playing.")



@bot.command()
async def resume(ctx):
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("Music resumed.")
    else:
        await ctx.send("Music is not paused.")



@bot.command()
async def volume(ctx, vol: int):
    if ctx.voice_client is None:
        await ctx.send("I'm not connected to a voice channel.")
        return

    if vol < 0 or vol > 100:
        await ctx.send("Please provide a volume between 0 and 100.")
        return

    ctx.voice_client.source = discord.PCMVolumeTransformer(ctx.voice_client.source)
    ctx.voice_client.source.volume = vol / 100
    await ctx.send(f"Volume set to {vol}%")



@bot.command()
async def queue(ctx):
    global song_queue
    if len(song_queue) > 0:
        queue_list = "\n".join(song_queue)
        await ctx.send(f"**Queue:**\n{queue_list}")
    else:
        await ctx.send("The queue is currently empty.")



@bot.command()
async def clear(ctx):
    global song_queue
    song_queue = []
    await ctx.send("Queue cleared.")



@bot.command()
async def nowplaying(ctx):
    global current_song

    if current_song:
        ytdl = youtube_dl.YoutubeDL(ytdl_opts)
        info = ytdl.extract_info(current_song, download=False)
        await ctx.send(f"Now playing: {info['title']}")
    else:
        await ctx.send("No music is currently playing.")



@bot.command()
async def skip(ctx):
    global is_playing
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        is_playing = False
        await ctx.send("Skipping the current song...")
    else:
        await ctx.send("No music is currently playing.")



@bot.command()
async def info(ctx):
    info_message = (
        "**Music Bot Commands**\n"
        "`!play <name or URL>`: Play a single song from YouTube or add it to the queue.\n"
        "`!playlist <playlist URL>`: Play all songs in a YouTube playlist.\n"
        "`!stop`: Stop the current song and disconnect from the voice channel.\n"
        "`!pause`: Pause the current song.\n"
        "`!resume`: Resume the paused song.\n"
        "`!skip`: Skip the current song.\n"
        "`!volume <1-100>`: Set the volume of the bot.\n"
        "`!nowplaying`: Show the currently playing song.\n"
        "`!queue`: Show the current queue.\n"
        "`!clear`: Clear the queue.\n"
    )

    await ctx.send(info_message)



bot.run(TOKEN)