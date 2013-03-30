import os, sys
import numpy as np
import cv2
from time import sleep
from multiprocessing import Process, Pipe, Event
from multiprocessing.sharedctypes import RawValue, Value
# RawValue is shared memory without lock, handle with care, this is usefull for ATB it needs cTypes
from eye import eye, eye_profiled
from world import world, world_profiled
from player import player
from methods import Temp

# import pyaudio
# import waveatb.
# from audio import normalize, trim, add_silence

from ctypes import c_bool, c_int

def main():
    auto_assing_cameras = False
    if not auto_assing_cameras:
        #manually assign the right id to the cameras
        eye_src = 0
        world_src = 1
    else:
        eye_src = None
        world_src = None
        from v4l2_ctl import list_devices
        for d in list_devices():
            print "found Camera: "+d["name"]
            if "6000" in d["name"]:
                eye_src = d["src_id"]
            elif "C510" or "C525" or "C615" in d["name"]:
                world_src = d["src_id"]
        if eye_src is None:
            print "Error: Auto_assing_cameras could not detect eye camera, please check if you have the camera attached"
            return
        if world_src is None:
            print "Error: Auto_assing_cameras could not detect world camera, please check if you have the camera attached"
            return


    #video size
    eye_size = (416,240)
    """
        HD-6000
        v4l2-ctl -d /dev/video0 --list-formats-ext
        640x480 1280x720 960x544 800x448 640x360 800x600
        416x240 352x288 176x144 320x240 160x120
    """
    world_size = (1280,720)
    """
        c-525
        v4l2-ctl -d /dev/video0 --list-formats-ext
        640x480 160x120 176x144 320x176 320x240 432x240
        352x288 544x288 640x360 752x416 800x448 864x480
        960x544 1024x576 800x600 1184x656 960x720
        1280x720 1392x768 1504x832 1600x896 1280x960
        1712x960 1792x1008 1920x1080
    """


    # use the player: a seperate window for video playback and 9 point calibration animation
    use_player = 1

    player_size = (800,600) #this can be whatever you like


    #use video for debugging
    use_video = 0

    audio = False

    if use_video:
        eye_src = "/Users/mkassner/Pupil/pupil_google_code/wiki/videos/green_eye_VISandIR_2.mov" # using a path to a videofiles allows for developement without a headset.
        world_src = 0

    # create shared globals
    g_pool = Temp()
    g_pool.gaze_x = Value('d', 0.0)
    g_pool.gaze_y = Value('d', 0.0)
    g_pool.pattern_x = Value('d', 0.0)
    g_pool.pattern_y = Value('d', 0.0)
    g_pool.frame_count_record = Value('i', 0)
    g_pool.calibrate = RawValue(c_bool, 0)
    g_pool.cal9 = RawValue(c_bool, 0)
    g_pool.cal9_stage = Value('i', 0)
    g_pool.cal9_step = Value('i', 0)
    g_pool.cal9_circle_id = RawValue('i' ,0)
    g_pool.pos_record = Value(c_bool, 0)
    g_pool.eye_rx, g_pool.eye_tx = Pipe(False)

    g_pool.audio_record = Value(c_bool,False)
    g_pool.audio_rx, g_pool.audio_tx = Pipe(False)
    g_pool.player_refresh = Event()
    g_pool.play = RawValue(c_bool,0)
    g_pool.quit = RawValue(c_bool,0)
    # end shared globals

    # set up sub processes
    p_eye = Process(target=eye, args=(eye_src,eye_size, g_pool))
    if use_player: p_player = Process(target=player, args=(g_pool,player_size))
    if audio: p_audio = Process(target=record_audio, args=(g_pool.audio_rx,g.g_pool.audio_record,3))

    # spawn sub processes
    if use_player: p_player.start()
    p_eye.start()
    if audio: p_audio.start()

    # on linux we need to give the camera driver some time before you request another camera
    sleep(1)

    # on Mac, when using some cameras (like our current worldcamera logitch c510)
    # you can't run world camera grabber in its own process
    # it must reside in the main loop when you run on MacOS.
    world(world_src,world_size,g_pool)

    # exit / clean-up
    p_eye.join()
    if use_player: p_player.join()
    if audio: p_audio.join()
    print "main exit"

if __name__ == '__main__':
    main()
