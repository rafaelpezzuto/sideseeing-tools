import os

import imageio
import cv2

from moviepy.editor import VideoFileClip


def extract_audio(source_path: str, target_path: str, sample_rate=44100, channels=2, codec='pcm_s16le', overwrite=False):
    '''
    Extracts audio in WAV format from a video file.
    '''
    target_dir = os.path.dirname(target_path)

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    mp4_name = os.path.basename(source_path)
    wav_path = os.path.join(target_dir, mp4_name.replace('.mp4', '.wav'))

    if not os.path.exists(wav_path) or overwrite:
        print(f'INFO. Extracting WAV from {source_path} to {wav_path}.')
        clip = VideoFileClip(source_path)
        clip.audio.write_audiofile(wav_path, fps=sample_rate, nbytes=2, codec=codec, ffmpeg_params=["-ac", str(channels)])
        clip.close()

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


def extract_video_snippet(source_path, start_second, end_second, output_path):
    try:
        vc_reader = cv2.VideoCapture(source_path)
        if not vc_reader.isOpened():
            print('ERROR. Could not open the video file {source_path}.')
            return

        fps = vc_reader.get(cv2.CAP_PROP_FPS)
        total_frames = int(vc_reader.get(cv2.CAP_PROP_FRAME_COUNT))
        height = int(vc_reader.get(cv2.CAP_PROP_FRAME_HEIGHT))
        width = int(vc_reader.get(cv2.CAP_PROP_FRAME_WIDTH))
        
        start_frame = int(fps * start_second)
        end_frame = min(int(fps * end_second), total_frames)

        if start_frame >= end_frame:
            raise ValueError('ERROR. End time must be greater than start time.')
        
        print(f'INFO. Extracting snippet from second {start_second} to {end_second}.')    
        vc_writer = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
        
        for fn in range(start_frame, end_frame):
            vc_reader.set(cv2.CAP_PROP_POS_FRAMES, fn)
            success, frame = vc_reader.read()
            if success:
                vc_writer.write(frame)
    
    except Exception as e:
        print(f'Error occurred: {str(e)}')

    finally:
        vc_writer.release()
        vc_reader.release()
