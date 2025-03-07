import time

import yt_dlp
from aiogram import F, Router, types, exceptions
from youthon import Video

from handlers.modules.master import master_handler

router = Router()


def get_ydl_opts(quality: str, filename: str) -> dict:
    formats = {
        "fhd": {"format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]", "merge_output_format": "mp4", "postprocessor_args": ["-c:v", "h264", "-c:a", "aac"]},
        "hd": {"format": "best[height<=720][ext=mp4]"},
        "sd": {"format": "best[height<=480][ext=mp4]"},
        "audio": {"format": "bestaudio[ext=m4a]", "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]},
    }
    opts = {"outtmpl": filename, "postprocessors": [{"key": "FFmpegFixupM4a"}, {"key": "FFmpegFixupStretched"}]}
    return {**opts, **formats[quality]}


def download_youtube(url: str, filename: str, quality: str) -> str:
    fname = filename[:-4] if quality in ["best", "fhd", "audio"] else filename
    with yt_dlp.YoutubeDL(get_ydl_opts(quality, fname)) as ydl:
        ydl.download([url])
    return filename


links = [
    "https://www.youtube.com/watch?v=",
    "https://youtu.be/",
    "https://www.youtube.com/shorts/",
    "https://youtube.com/shorts/",
]


def check_fhd_availability(url: str) -> bool:
    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        info = ydl.extract_info(url, download=False)
        fhd_format = next(f for f in info["formats"] if f.get("height") == 1080)
        filesize = fhd_format.get("filesize")
        return filesize <= 100 * 1024 * 1024


def keyboard(url: str) -> types.InlineKeyboardMarkup:
    kb = []
    if check_fhd_availability(url):
        kb.append([types.InlineKeyboardButton(text="📹 Full HD (1080p) (Долго)", callback_data=f"{url}!fhd")])
    kb.append([types.InlineKeyboardButton(text="📹 HD (720p) (Быстро)", callback_data=f"{url}!hd")])
    kb.append([types.InlineKeyboardButton(text="📹 SD (480p) (Быстро)", callback_data=f"{url}!sd")])
    kb.append([types.InlineKeyboardButton(text="🎵 Только аудио", callback_data=f"{url}!audio")])
    
    return types.InlineKeyboardMarkup(inline_keyboard=kb)


@router.message(F.text.startswith(tuple(links)))
async def youtube(message: types.Message) -> None:
    try:
        await message.answer_photo(
            photo=Video(message.text).thumbnail_url,
            caption="Выберите качество загрузки:",
            reply_markup=keyboard(message.text),
        )
        await message.delete()
    except Exception:
        await message.answer("Ошибка при получении данных видео.")



@router.callback_query(lambda c: c.data.startswith(tuple(links)))
async def process_download(callback: types.CallbackQuery) -> None:
    url, quality = callback.data.split("!")
    extension = "mp3" if quality == "audio" else "mp4"
    filename = f"{time.time_ns()}-{callback.message.from_user.id}.{extension}"

    await master_handler(
        message=callback.message,
        send_function=callback.message.answer_video if quality != "audio" else callback.message.answer_audio,
        download_function=lambda: download_youtube(url, filename, quality),
    )
