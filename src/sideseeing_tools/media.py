import os

import cv2
import imageio
from moviepy import AudioFileClip, VideoFileClip

from sideseeing_tools.snippets import resolve_snippet_time_bounds


def extract_audio(
    source_path, target_path, sample_rate=44100, channels=2, codec='pcm_s16le', overwrite=False
):
    """Extracts audio in WAV format from a video file."""
    target_dir = os.path.dirname(target_path)

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    mp4_name = os.path.basename(source_path)
    wav_path = os.path.join(target_dir, mp4_name.replace('.mp4', '.wav'))

    if not os.path.exists(wav_path) or overwrite:
        print(f'INFO. Extracting WAV from {source_path} to {wav_path}.')
        clip = VideoFileClip(source_path)
        clip.audio.write_audiofile(
            wav_path, fps=sample_rate, nbytes=2, codec=codec, ffmpeg_params=["-ac", str(channels)]
        )
        clip.close()

    return wav_path


def extract_gif(source_path, target_path, target_width=300, target_fps=5):
    """Extracts a tiny video in GIF format from a video file."""
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
        target_height = int(
            cap.get(cv2.CAP_PROP_FRAME_HEIGHT) * (target_width / cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        )
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
    with VideoFileClip(str(source_path)) as source:
        start_second, end_second = resolve_snippet_time_bounds(
            start_second, end_second, source.duration
        )

        with source.subclipped(start_second, end_second) as snippet:
            snippet.write_videofile(str(output_path))

    return output_path


def extract_audio_snippet(source_path, start_second, end_second, output_path):
    codec = 'pcm_s16le' if str(output_path).lower().endswith('.wav') else 'aac'

    with AudioFileClip(str(source_path)) as source:
        start_second, end_second = resolve_snippet_time_bounds(
            start_second, end_second, source.duration
        )

        with source.subclipped(start_second, end_second) as snippet:
            snippet.write_audiofile(str(output_path), codec=codec)

    return output_path


def extract_frames_at_times(source_path, frame_times, target_dir=None, prefix='', left_zeros=5):
    """Return frames at requested seconds, or saved paths when target_dir is supplied."""
    paths = []
    frames = []

    try:
        cap = cv2.VideoCapture(source_path)
        fps = cap.get(cv2.CAP_PROP_FPS)

        frame_positions = [int(time * fps) for time in frame_times]

        for i in frame_positions:
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()

            if ret:
                frame_name = f'{prefix}{str(i).zfill(left_zeros)}.jpg'

                if target_dir:
                    frame_path = os.path.join(target_dir, frame_name)
                    cv2.imwrite(frame_path, frame)
                    paths.append(frame_path)
                else:
                    frames.append(frame)
            else:
                break

    except FileNotFoundError:
        print(f'ERROR. Source file not found. Check the file path {source_path}.')

    except Exception as e:
        print(f'Error occurred: {str(e)}')

    finally:
        if 'cap' in locals():
            cap.release()

    if target_dir:
        return paths
    else:
        return frames


def extract_frames_at_positions(
    source_path, frame_positions, target_dir=None, prefix='', left_zeros=5
):
    """Return frames at requested positions, in memory or as saved paths."""
    paths = []
    frames = []

    try:
        cap = cv2.VideoCapture(source_path)

        for i in frame_positions:
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()

            if ret:
                frame_name = f'{prefix}{str(i).zfill(left_zeros)}.jpg'

                if target_dir:
                    frame_path = os.path.join(target_dir, frame_name)
                    cv2.imwrite(frame_path, frame)
                    paths.append(frame_path)
                else:
                    frames.append(frame)
            else:
                break

    except FileNotFoundError:
        print(f'ERROR. Source file not found. Check the file path {source_path}.')

    except Exception as e:
        print(f'Error occurred: {str(e)}')

    finally:
        if 'cap' in locals():
            cap.release()

    if target_dir:
        return paths
    else:
        return frames


def extract_frames_timespan(
    source_path, start_time, end_time, target_dir=None, step=None, prefix='', left_zeros=5
):
    """Return frames within an interval in seconds, in memory or as saved paths."""
    paths = []
    frames = []

    try:
        cap = cv2.VideoCapture(source_path)
        fps = cap.get(cv2.CAP_PROP_FPS)

        if not step:
            step = int(fps)

        if step <= 0:
            raise ValueError("step must be greater than 0.")

        start_frame = int(start_time * fps)
        end_frame = int(end_time * fps)

        frame_positions = [i for i in range(start_frame, end_frame, step)]

        for i in frame_positions:
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()

            if ret:
                frame_name = f'{prefix}{str(i).zfill(left_zeros)}.jpg'

                if target_dir:
                    frame_path = os.path.join(target_dir, frame_name)
                    cv2.imwrite(frame_path, frame)
                    paths.append(frame_path)
                else:
                    frames.append(frame)
            else:
                break

    except FileNotFoundError:
        print(f'ERROR. Source file not found. Check the file path {source_path}.')

    except Exception as e:
        print(f'Error occurred: {str(e)}')

    finally:
        if 'cap' in locals():
            cap.release()

    if target_dir:
        return paths
    else:
        return frames


def extract_frames_positionspan(
    source_path, start_frame, end_frame, target_dir=None, step=None, prefix='', left_zeros=5
):
    """Return frames within a position interval, in memory or as saved paths."""
    paths = []
    frames = []

    try:
        cap = cv2.VideoCapture(source_path)
        fps = cap.get(cv2.CAP_PROP_FPS)

        if not step:
            step = int(fps)

        if step <= 0:
            raise ValueError("step must be greater than 0.")

        if start_frame > end_frame:
            raise ValueError("Start frame position cannot be greater than the end frame position.")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if end_frame > total_frames:
            end_frame = total_frames
            print(
                f'WARNING. End frame position is greater than the total number of frames. Setting end frame to {total_frames}.'
            )

        frame_positions = [i for i in range(start_frame, end_frame, step)]

        for i in frame_positions:
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()

            if ret:
                frame_name = f'{prefix}{str(i).zfill(left_zeros)}.jpg'

                if target_dir:
                    frame_path = os.path.join(target_dir, frame_name)
                    cv2.imwrite(frame_path, frame)
                    paths.append(frame_path)
                else:
                    frames.append(frame)
            else:
                break

    except FileNotFoundError:
        print(f'ERROR. Source file not found. Check the file path {source_path}.')

    except Exception as e:
        print(f'Error occurred: {str(e)}')

    finally:
        if 'cap' in locals():
            cap.release()

    if target_dir:
        return paths
    else:
        return frames


def extract_frames(source_path, target_dir=None, step=None, prefix='', left_zeros=5):
    """Return regularly spaced frames, or saved paths when target_dir is supplied."""
    paths = []
    frames = []

    try:
        cap = cv2.VideoCapture(source_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        if not step:
            step = int(fps)

        if step <= 0:
            raise ValueError("step must be greater than 0.")

        frame_positions = [i for i in range(0, total_frames, step)]

        for i in frame_positions:
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()

            if ret:
                frame_name = f'{prefix}{str(i).zfill(left_zeros)}.jpg'

                if target_dir:
                    frame_path = os.path.join(target_dir, frame_name)
                    cv2.imwrite(frame_path, frame)
                    paths.append(frame_path)
                else:
                    frames.append(frame)
            else:
                break

    except FileNotFoundError:
        print(f'ERROR. Source file not found. Check the file path {source_path}.')

    except Exception as e:
        print(f'Error occurred: {str(e)}')

    finally:
        if 'cap' in locals():
            cap.release()

    if target_dir:
        return paths
    else:
        return frames
