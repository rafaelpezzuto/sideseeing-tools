import os

import imageio
import cv2


from moviepy import VideoFileClip


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
        snippet = (
            VideoFileClip(source_path)
            .subclipped(start_second, end_second)
        )
        snippet.write_videofile(output_path)

    except FileNotFoundError:
        print(f'ERROR. Source file not found. Check the file path {source_path}.')

    except Exception as e:
        print(f'Error occurred: {str(e)}')

    finally:
        if 'snippet' in locals():
            snippet.close()


def extract_frames_at_times(source_path, frame_times: list, target_dir=None, prefix='', left_zeros=5):
    '''
    Extracts frames from a video file at the specified time points and saves them as image files.
    
    Args:
        source_path (str): Path to the source video file.
        frame_times (list): List of time points (in seconds) at which frames should be extracted.
        target_dir (str): Path to the target directory where frames will be saved.
        prefix (str, optional): Prefix to be added to the frame file names.
        left_zeros (int, optional): Number of left-padded zeros in the frame file names.

    Returns:
        list: List of paths to the extracted frames.
    '''
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


def extract_frames_at_positions(source_path, frame_positions: list, target_dir=None, prefix='', left_zeros=5):
    '''
    Extracts frames from a video file at the specified frame positions and saves them as image files.
    
    Args:
        source_path (str): Path to the source video file.
        frame_positions (list): List of frame positions at which frames should be extracted.
        target_dir (str): Path to the target directory where frames will be saved.
        prefix (str, optional): Prefix to be added to the frame file names.
        left_zeros (int, optional): Number of left-padded zeros in the frame file names.

    Returns:
        list: List of paths to the extracted frames.
    '''
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


def extract_frames_timespan(source_path, start_time, end_time, target_dir=None, step=None, prefix='', left_zeros=5):
    '''
    Extracts frames from a video file within a specified time span and saves them as image files.
    
    Args:
        source_path (str): The path to the source video file.
        start_time (float): The start time (in seconds) of the time span from which frames should be extracted.
        end_time (float): The end time (in seconds) of the time span from which frames should be extracted.
        target_dir (str): The directory where the extracted frames will be saved.
        step (int, optional): The rate at which frames are extracted.
        prefix (str, optional): A prefix for the saved frame filenames. Default is an empty string.
        left_zeros (int, optional): The number of leading zeros in the frame filenames. Default is 5.
    
    Raises:
        FileNotFoundError: If the source video file is not found.
        Exception: For any other exceptions that occur during the frame extraction process.

    Returns:
        list: List of paths to the extracted frames.
    '''
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


def extract_frames_positionspan(source_path, start_frame, end_frame, target_dir=None, step=None, prefix='', left_zeros=5):
    '''
    Extracts frames from a video file within a specified position span and saves them as image files.
    
    Args:
        source_path (str): The path to the source video file.
        start_frame (int): The start frame position from which frames should be extracted.
        end_frame (int): The end frame position from which frames should be extracted.
        target_dir (str): The directory where the extracted frames will be saved.
        step (int): The rate at which frames are extracted.
        prefix (str, optional): A prefix for the saved frame filenames. Default is an empty string.
        left_zeros (int, optional): The number of leading zeros in the frame filenames. Default is 5.
        
    Raises:
        FileNotFoundError: If the source video file is not found.
        Exception: For any other exceptions that occur during the frame extraction process.

    Returns:
        list: List of paths to the extracted frames.
    '''
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
            print(f'WARNING. End frame position is greater than the total number of frames. Setting end frame to {total_frames}.')

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
    """
    Extracts frames from a video file at a specified frame rate and saves them as image files.
    
    Args:
        source_path (str): The path to the source video file.
        target_dir (str): The directory where the extracted frames will be saved.
        step (int): The rate at which frames are extracted.
        prefix (str, optional): A prefix for the saved frame filenames. Default is an empty string.
        left_zeros (int, optional): The number of leading zeros in the frame filenames. Default is 5.
     
    Raises:
        FileNotFoundError: If the source video file is not found.
        Exception: For any other exceptions that occur during the frame extraction process.
    
    Notes:
        The function uses OpenCV to read the video file and extract frames. The frames are saved as JPEG files in the specified target directory.

    Returns:
        list: List of paths to the extracted frames.
    """
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
