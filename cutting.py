import os, sys
import time, re, json, shutil
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
    subprocess.check_call(f'{FFMPEG} -i "{video_in}" -ss {tstart}{endstr}-vcodec libx264 -acodec libvo_aacenc -y {trimmed_file}', shell=True)
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
    work_filename = f"convert-{start_time}.wav"
    out_filepath = os.path.join(TMP_PATH, out_filename)
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
    if dev_mode:
        _req_video=os.path.join(APP_PATH, "sample.mp4")
        _req_text = "start-cut-video@00:00:10;end-cut-video@ 19 Seconds"
        #print('devmode')
    #print(model_request_dict)
    if isinstance(_req_video, list):
        _req_video = str(_req_video[0])

    #convert_audio = trim_sound_file(_req_audio, work_filepath, 30)
    #REMOVE OLD INPUTS
    #try:
    #    shutil.rmtree(IN_PATH)
    #except OSError as e:
    #    print("Error: %s - %s." % (e.filename, e.strerror))
    #os.makedirs(args.IN_PATH, exist_ok=True)

    filename = os.path.basename(_req_video)
    file_ext = os.path.splitext(filename)[1]

    # INPUT File Path    
    #in_filename = f'video-input.{file_ext}'
    #in_filepath = os.path.join(IN_PATH, in_filename)

    ##TODO##
    #with requests.get(_req_audio, stream=True) as r:
    #        with open(in_filepath, 'wb') as f:
    #            shutil.copyfileobj(r.raw, f)
    

    # Run Model
    if _req_text:
        

        #_req_text = "Start@00:00:10;End@ 25 Seconds"
        _req_keys = _req_text.split(";")
        _now = datetime.now()
        for _key in _req_keys:
            if _key.startswith("start-cut-video@"):
                _start = _key.split("@")
                _startStr = _start[1]
                try:
                    _startDS = datetime.strptime(_startStr, '%H:%M:%S')
                    _startDS = datetime.strftime(_startDS, "%H:%M:%S")
                    _startDS = f"{_startDS}.000"
                except ValueError as e:
                    try:
                        _startDS = dateparser.parse(_startStr)
                        _startDS = _now - _startDS
                    except TypeError as e2:
                        _startDS = "00:00:00.000"

                #_startDS = datetime.date.strftime(_startDS, "%H:%M:%S")
            if _key.startswith("end-cut-video@"):
                _end = _key.split("@")
                _endStr = _end[1]
                try:
                    _endDS = datetime.strptime(_endStr, '%H:%M:%S')
                    _endDS = datetime.strftime(_endDS, "%H:%M:%S")
                    _endDS = f"{_endDS}.000"
                except ValueError as e:
                    try:
                        _endDS = dateparser.parse(_endStr)
                        _endDS = _now - _endDS
                    except TypeError as e2:
                        _endDS = "MAXTIME"

        
        try:
            outfile = trim_video(_req_video, out_filepath, _startDS, _endDS)
        except:
            outfile = 'error running ffmpeg'
            print(outfile)
            exit(1)

    if not os.path.isfile(out_filepath):
        print(f"[ ERROR ] -> DeSotavidcutter Request Failed: No Output found")
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

        print(f"[ INFO ] -> DeSota vidcutter Response:{out_filepath}")

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
            print(f"[ ERROR ] -> DeSotaControlAudio Post Failed (Info):\nfiles: {files}\nResponse Code: {send_task.status_code}")
            exit(3)
    
    print("TASK OK!")
    exit(0)


if __name__ == "__main__":
    args = parser.parse_args()
    if not args.model_req or not args.model_res_url:
        raise EnvironmentError()
    main(args)
