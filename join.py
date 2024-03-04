import os, sys
import time, re, json, shutil
from subprocess import CalledProcessError
import requests, subprocess, random
import argparse
import dateparser
from datetime import datetime

os.environ['CURL_CA_BUNDLE'] = ''

from requests.adapters import HTTPAdapter, Retry

s = requests.Session()

retries = Retry(total=5,
                backoff_factor=0.1,
                status_forcelist=[ 500, 502, 503, 504 ])

s.mount('https://', HTTPAdapter(max_retries=retries))

parser = argparse.ArgumentParser()
parser.add_argument("-mr", "--model_req", 
                    help="DeSOTA Request as yaml file path",
                    type=str)
parser.add_argument("-mru", "--model_res_url",
                    help="DeSOTA API Result URL. Recognize path instead of url for desota tests", # check how is atribuited the dev_mode variable in main function
                    type=str)

DEBUG = False
CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
# DeSOTA Funcs [START]
#   > Import DeSOTA Scripts
from desota import detools
#   > Grab DeSOTA Paths
USER_SYS = detools.get_platform()
APP_PATH = os.path.dirname(os.path.realpath(__file__))
TMP_PATH = os.path.join(CURRENT_PATH, f"tmp")
#IN_PATH = os.path.join(CURRENT_PATH, f"in")
#   > USER_PATH
if USER_SYS == "win":
    path_split = str(APP_PATH).split("\\")
    desota_idx = [ps.lower() for ps in path_split].index("desota")
    USER=path_split[desota_idx-1]
    USER_PATH = "\\".join(path_split[:desota_idx])
elif USER_SYS == "lin":
    path_split = str(APP_PATH).split("/")
    desota_idx = [ps.lower() for ps in path_split].index("desota")
    USER=path_split[desota_idx-1]
    USER_PATH = "/".join(path_split[:desota_idx])
DESOTA_ROOT_PATH = os.path.join(USER_PATH, "Desota")
CONFIG_PATH = os.path.join(DESOTA_ROOT_PATH, "Configs")
SERV_CONF_PATH = os.path.join(CONFIG_PATH, "services.config.yaml")
# DeSOTA Funcs [END]
#SET FOR TRANSFORMERS ENV::
ENV_PATH = os.path.join(DESOTA_ROOT_PATH,"Portables","Transformers")
FFMPEG = os.path.join(ENV_PATH,"env","Library","bin","ffmpeg.exe")
FFPROBE = os.path.join(ENV_PATH,"env","Library","bin","ffprobe.exe")


def trim_video(video_in, video_out, tstart, tend):
    # Trim the input sound file to a maximum length of 30 seconds
    trimmed_file = video_out # f"trimmed_{soundfile}"
    #ffmpeg -i file.mp3 -ar 16000 -ac 1 -b:a 96K -acodec pcm_s16le file.wav
    if tstart == "MAXTIME":
        endstr = " "
    else:
        endstr = f" -to {tend} "
    subprocess.check_call(f'{FFMPEG} -i "{video_in}" -ss {tstart}{endstr}-vcodec libx264 -acodec aac -y {trimmed_file} ', shell=False)
    #subprocess.check_call(f'ffmpeg -i {soundfile} -t {tmax} -y {trimmed_file}', shell=True)
    #print(f"Trimmed sound file saved as: {trimmed_file}")
    return trimmed_file

def trim_sound_file(soundfile, trim_file, tmax):
    # Trim the input sound file to a maximum length of 30 seconds
    trimmed_file = trim_file # f"trimmed_{soundfile}"
    #ffmpeg -i file.mp3 -ar 16000 -ac 1 -b:a 96K -acodec pcm_s16le file.wav
    subprocess.check_call(f'{FFMPEG} -i {soundfile} -ar 16000 -ac 1 -b:a 96K -acodec pcm_s16le -y {trimmed_file}', shell=True)
    #subprocess.check_call(f'ffmpeg -i {soundfile} -t {tmax} -y {trimmed_file}', shell=True)
    #print(f"Trimmed sound file saved as: {trimmed_file}")
    return trimmed_file

def extract_sound_length(soundfile):
    # Extract the length of the sound file in seconds
    result = subprocess.check_output(f'{FFPROBE} -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {soundfile}', shell=True)
    length = int(float(result))
    #print(f"Sound file length: {length} seconds")
    return length

def main(args):
    '''
    return codes:
    0 = SUCESS
    1 = INPUT ERROR
    2 = OUTPUT ERROR
    3 = API RESPONSE ERROR
    9 = REINSTALL MODEL (critical fail)
    '''
    print('hello')
    if not os.path.exists(TMP_PATH):
        os.makedirs(TMP_PATH)
    for filename in os.listdir(TMP_PATH):
        file_path = os.path.join(TMP_PATH, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))
    
   # Time when grabed
    _report_start_time = time.time()
    start_time = int(_report_start_time)

    #---INPUT---# TODO (PRO ARGS)
    _resnum = 5
    #---INPUT---#

    # DeSOTA Model Request
    model_request_dict = detools.get_model_req(args.model_req)
    
    # API Response URL
    send_task_url = args.model_res_url
    
    # TARGET File Path
    out_filename = f"result-{start_time}.mp4"
    out_filenameWA = f"resultWA-{start_time}.mp4"
    work_filename = f"convert-{start_time}.wav"
    out_filepath = os.path.join(TMP_PATH, out_filename)
    out_filepathWA = os.path.join(TMP_PATH, out_filenameWA)
    work_filepath = os.path.join(TMP_PATH, work_filename)
    
    out_urls = detools.get_url_from_str(send_task_url)
    if len(out_urls)==0:
        dev_mode = True
        report_path = send_task_url
    else:
        dev_mode = False
        report_path = out_urls[0]

    # Get text from request
    _req_text = detools.get_request_text(model_request_dict)
    if isinstance(_req_text, list):
        _req_text = ";".join(_req_text)
    if DEBUG:
        with open(os.path.join(APP_PATH, "debug.txt"), "w") as fw:
            fw.writelines([
                f"INPUT: '{_req_text}'\n",
                f"IsINPUT?: {True if _req_text else False}\n"
            ])
    
    
    # TODO Get VIDEO from request TODO
    ##TODO##
    _req_video = detools.get_request_video(model_request_dict) ##TODO##
    _req_image = detools.get_request_image(model_request_dict) ##TODO##
    _req_audio = detools.get_request_audio(model_request_dict) ##TODO##
    _resources = []
    if _req_video:
        _resources = _req_video
    if _req_image:
        _resources += _req_image

    if dev_mode:
        _resources=[os.path.join(APP_PATH, "sample.mp4"),os.path.join(APP_PATH, "sample.mp4")]
        _req_text = "start-cut-video@00:00:10;end-cut-video@ 1 minute 25 Seconds"
        print('devmode')
        #print(_req_video)
    #print(model_request_dict)


    #convert_audio = trim_sound_file(_req_audio, work_filepath, 30)
    #REMOVE OLD INPUTS
    #try:
    #    shutil.rmtree(IN_PATH)
    #except OSError as e:
    #    print("Error: %s - %s." % (e.filename, e.strerror))
    #os.makedirs(args.IN_PATH, exist_ok=True)

    #filename = os.path.basename(_req_video)
    #file_ext = os.path.splitext(filename)[1]

    # INPUT File Path    
    #in_filename = f'video-input.{file_ext}'
    #in_filepath = os.path.join(IN_PATH, in_filename)

    ##TODO##
    #with requests.get(_req_audio, stream=True) as r:
    #        with open(in_filepath, 'wb') as f:
    #            shutil.copyfileobj(r.raw, f)
    

    # Run Model
    if _req_text:
        video_width = 1920
        video_height = 1080
        audioSources = _req_audio
        if audioSources:
            output_audio_path = os.path.join(TMP_PATH, audioSources[0])
        else:
            audioSources=[]
        input_files=[]
        total_audio_duration = 0
        if len(audioSources)>1:
            # Create audio clips and add them to the input files list
            for audioSource in audioSources:
                input_files.extend(["-i", audioSource])

            # Concatenate the audio clips into a single audio file
            output_audio_path = os.path.join(TMP_PATH, 'audio' + ".wav")
            subprocess.call([f"{FFMPEG}"] + input_files + ["-filter_complex", "concat=n={}:v=0:a=1".format(len(audioSources)), "-vn -y ", output_audio_path])

            # Get the total duration of the concatenated audio clip
            total_audio_duration = subprocess.check_output([f"{FFPROBE}", "-i", output_audio_path, "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"]).decode("utf-8").strip()
        elif len(audioSources)==1:
            print(audioSources)
            total_audio_duration = subprocess.check_output([f"{FFPROBE}", "-i", str(audioSources[0]), "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"]).decode("utf-8").strip()

        if int(total_audio_duration)<10:
            total_audio_duration=len(_resources)*10

        print(total_audio_duration)

        input_files = []
        for _resource in _resources:
            if _resource.endswith((".mp4", ".m4a", ".mov", ".webm", ".avi", ".mkv")):
                # Create a video clip, resize it to the maximum height while maintaining aspect ratio, center it both horizontally and vertically, apply a blur effect, and pad to the maximum width with a transparent color
                try:
                    #subprocess.check_call(f"{FFMPEG} -i "+ str(_resource)+ " -vcodec libx264 -vf scale="+str(video_width)+":"+str(video_height)+":force_original_aspect_ratio=decrease,pad="+str(video_width)+":"+str(video_height)+":-1:-1:color=#00000000,crop=w=iw*0.96,split[original][copy];[copy]scale="+str(int(video_width)*2)+":"+str(int(video_height)*2)+":force_original_aspect_ratio=increase,crop="+str(video_width)+":"+str(video_height)+",gblur=sigma=22[blurred];[blurred][original]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2 -c:a copy -t "+ str(float(total_audio_duration)/len(_resources)) + " -y " + str(os.path.join(TMP_PATH, "resized_" + os.path.splitext(os.path.basename(_resource))[0]) + ".mp4"))
                    subprocess.check_call(f"{FFMPEG} -i "+ str(_resource)+ " -vcodec libx264 -vf scale="+str(video_width)+":"+str(video_height)+":force_original_aspect_ratio=decrease,pad="+str(video_width)+":"+str(video_height)+":-1:-1:color=#00000000,crop=w=iw*0.96,split[original][copy];[copy]scale="+str(int(video_width)*2)+":"+str(int(video_height)*2)+":force_original_aspect_ratio=increase,crop="+str(video_width)+":"+str(video_height)+",gblur=sigma=22[blurred];[blurred][original]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2 -c:a copy -y " + str(os.path.join(TMP_PATH, "resized_" + os.path.splitext(os.path.basename(_resource))[0]) + ".mp4"))
                    input_files.extend(["-i", str(os.path.join(TMP_PATH, "resized_" + os.path.splitext(os.path.basename(_resource))[0])+".mp4")])
                except CalledProcessError as e:
                    print(e.output)
                    print(":WILL RETRY!!!")
                    #subprocess.check_call(f"{FFMPEG} -i "+ str(_resource)+ " -vcodec libx264 -vf scale="+str(video_width)+":"+str(video_height)+":force_original_aspect_ratio=decrease,pad="+str(video_width)+":"+str(video_height)+":-1:-1:color=#00000000,crop=w=iw*0.96,split[original][copy];[copy]scale="+str(int(video_width)*2)+":"+str(int(video_height)*2)+":force_original_aspect_ratio=increase,crop="+str(video_width)+":"+str(video_height)+",gblur=sigma=22[blurred];[blurred][original]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2 -c:a copy -t "+ str(float(total_audio_duration)/len(_resources)) + " -y " + str(os.path.join(TMP_PATH, "resized_" + os.path.splitext(os.path.basename(_resource))[0]) + ".mp4"))
                    subprocess.check_call(f"{FFMPEG} -i "+ str(_resource)+ " -vcodec libx264 -vf scale="+str(video_width)+":"+str(video_height)+":force_original_aspect_ratio=decrease,pad="+str(video_width)+":"+str(video_height)+":-1:-1:color=#00000000,crop=w=iw*0.96,split[original][copy];[copy]scale="+str(int(video_width)*2)+":"+str(int(video_height)*2)+":force_original_aspect_ratio=increase,crop="+str(video_width)+":"+str(video_height)+",gblur=sigma=22[blurred];[blurred][original]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2 -c:a copy -y " + str(os.path.join(TMP_PATH, "resized_" + os.path.splitext(os.path.basename(_resource))[0]) + ".mp4"))
                    input_files.extend(["-i", str(os.path.join(TMP_PATH, "resized_" + os.path.splitext(os.path.basename(_resource))[0])+".mp4")])
            elif _resource.endswith((".jpg", ".jpeg", ".png")):
                # Create an image clip, resize it to the maximum height while maintaining aspect ratio, set its duration to the total audio duration, center it both horizontally and vertically, apply a blur effect, and pad to the maximum width with a transparent color
                subprocess.check_call(f"{FFMPEG} -loop 1 -i "+ str(_resource)+ " -vcodec libx264 -vf scale="+str(video_width)+":"+str(video_height)+":force_original_aspect_ratio=decrease,pad="+str(video_width)+":"+str(video_height)+":-1:-1:color=#00000000,crop=w=iw*0.96,split[original][copy];[copy]scale="+str(int(video_width)*2)+":"+str(int(video_height)*2)+":force_original_aspect_ratio=increase,crop="+str(video_width)+":"+str(video_height)+",gblur=sigma=20[blurred];[blurred][original]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2 -t "+ str(float(total_audio_duration)/len(_resources)) + " -y " + str(os.path.join(TMP_PATH, "resized_" + os.path.splitext(os.path.basename(_resource))[0]) + ".mp4"))
                input_files.extend(["-i", str(os.path.join(TMP_PATH, "resized_" + os.path.splitext(os.path.basename(_resource))[0])+".mp4")])
            elif _resource.endswith(".gif"):
                # Create a gif clip, resize it to the maximum height while maintaining aspect ratio, center it both horizontally and vertically, apply a blur effect, and pad to the maximum width with a transparent color
                subprocess.check_call(f"{FFMPEG} -i "+ str(_resource)+ " -vcodec libx264 -vf scale="+str(video_width)+":"+str(video_height)+":force_original_aspect_ratio=decrease,pad="+str(video_width)+":"+str(video_height)+":-1:-1:color=#00000000,crop=w=iw*0.96,split[original][copy];[copy]scale="+str(int(video_width)*2)+":"+str(int(video_height)*2)+":force_original_aspect_ratio=increase,crop="+str(video_width)+":"+str(video_height)+",gblur=sigma=22[blurred];[blurred][original]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2 -t "+ str(float(total_audio_duration)/len(_resources)) + " -y " + str(os.path.join(TMP_PATH, "resized_" + os.path.splitext(os.path.basename(_resource))[0]) + ".mp4"))
                input_files.extend(["-i", str(os.path.join(TMP_PATH, "resized_" + os.path.splitext(os.path.basename(_resource))[0])+".mp4")])
            #i+=1
        # Combine the input files (audio and graphical) into the final output video file
        #output_video_path = os.path.join(TMP_PATH, outputName + "_{}x{}.mp4".format(video_width, video_height))
        subprocess.call([f"{FFMPEG}"] + input_files + ["-filter_complex", "concat=unsafe=1:n={}:v=1:a=0".format(len(_resources)), "-vsync", "2", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-tune", "animation", "-y", out_filepath])

        if audioSources:
            # Add some sounds
            subprocess.call(f"{FFMPEG} -i "+ str(out_filepath)+" -i " + str(output_audio_path)+ " -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 -y "+str(out_filepathWA))
            out_filepath = out_filepathWA

    if not os.path.isfile(out_filepath):
        print(f"[ ERROR ] -> DeSota vidjoinr Request Failed: No Output found")
        exit(2)
    
    if dev_mode:
        if not report_path.endswith(".json"):
            report_path += ".json"
        with open(report_path, "w") as rw:
            json.dump(
                {
                    "Model Result Path": out_filepath,
                    "Processing Time": time.time() - _report_start_time
                },
                rw,
                indent=2
            )
        detools.user_chown(report_path)
        detools.user_chown(out_filepath)
        print(f"Path to report:\n\t{report_path}")
    else:
        if DEBUG:
            with open(os.path.join(APP_PATH, "debug.txt"), "a") as fw:
                fw.write(f"RESULT: {out_filepath}")

        print(f"[ INFO ] -> DeSota vidjoinr Response:{out_filepath}")

        # DeSOTA API Response Preparation
        files = []
        with open(out_filepath, 'rb') as fr:
            files.append(('upload[]', fr))
            # DeSOTA API Response Post
            send_task = s.post(url = send_task_url, files=files)
            print(f"[ INFO ] -> DeSOTA API Upload:{json.dumps(send_task.json(), indent=2)}")
        # Delete temporary file
        os.remove(out_filepath)

        if send_task.status_code != 200:
            print(f"[ ERROR ] -> DeSota vidjoinr Post Failed (Info):\nfiles: {files}\nResponse Code: {send_task.status_code}")
            exit(3)
    
    print("TASK OK!")
    exit(0)


if __name__ == "__main__":
    args = parser.parse_args()
    if not args.model_req or not args.model_res_url:
        raise EnvironmentError()
    main(args)