import base64
import os
import subprocess

import cv2
import imageio

from IPython.display import (
    Audio, 
    HTML, 
    Image,
)


def extract_audio(source_path: str, target_path: str, sample_rate=44100, channels=2, codec='pcm_s16le'):
    '''
    Extracts audio in WAV format from a video file.
    '''
    target_dir = os.path.dirname(target_path)

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    mp4_name = os.path.basename(source_path)
    wav_path = os.path.join(target_dir, mp4_name.replace('.mp4', '.wav'))

    if not os.path.exists(wav_path):
        print(f'INFO. Extracting WAV from {source_path} to {wav_path}.')
        subprocess.call(['ffmpeg', '-i', source_path, '-vn', '-acodec', codec, '-ar', f'{sample_rate}', '-ac', f'{channels}', wav_path])

    return wav_path


def extract_gif(source_path: str, target_path: str, target_width=300, target_fps=5):
    '''
    Extracts a tiny video in GIF format from a video file.
    '''
    target_dir = os.path.dirname(target_path)

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    mp4_name = os.path.basename(source_path)
    gif_path = os.path.join(target_dir, mp4_name.replace('.mp4', '.gif'))

    if not os.path.exists(gif_path):
        print(f'INFO. Extracting GIF from {source_path} to {gif_path}.')

        cap = cv2.VideoCapture(source_path)
        original_fps = cap.get(cv2.CAP_PROP_FPS)

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        target_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) * (target_width / cap.get(cv2.CAP_PROP_FRAME_WIDTH)))
        target_resolution = (target_width, target_height)

        gif_frames_list = []
        frame_positions = [i for i in range(0, total_frames, int(original_fps) * 4)]

        for i in frame_positions:
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()

            if ret:
                if frame.shape[2] == 3:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                resized_frame = cv2.resize(frame, target_resolution)
                gif_frames_list.append(resized_frame)
            else:
                break

        imageio.mimsave(gif_path, gif_frames_list, fps=target_fps, subrectangles=True)

        cap.release()

    return gif_path


def play_video(path: str):
    '''
    Plays the video.
    '''
    mp4 = open(path,'rb').read()
    data_url = "data:video/mp4;base64," + base64.b64encode(mp4).decode()
    return HTML("""<video width=400 controls><source src="%s" type="video/mp4"></video>""" % data_url)


def play_gif(path: str):
    '''
    Displays the GIF.
    '''
    with open(path, 'rb') as f:
        display(Image(data=f.read(), format='png'))


def play_audio(path: str):
    '''
    Plays the audio track.
    '''
    return display(Audio(path))