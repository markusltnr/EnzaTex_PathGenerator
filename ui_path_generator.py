import yaml
import os
import cv2
import PySimpleGUI as sg
import numpy as np
from path_generator import path_generation
from camera import Camera
#from dummy_camera import Camera
import time
from datetime import datetime
import csv
import socket
from struct import *


TCP_IP="192.168.2.33"
TCP_PORT=10509

def socket_to_automat(ip, port, print_retry):
    currsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
    print(ip)
    print(port)
    try:        
        currsocket.connect((ip, port))
        currsocket.setblocking(0)
        print("Socket connected");
    except:
        if print_retry:
            print("Socket NOT connected, retrying")      
        else: 
            time.sleep(5)    
            socket_to_automat(ip, port, False)
    return currsocket

def send_to_socket(asocket, sample, coord):
    asocket.send(pack('i', int(sample))) 
    asocket.send(pack('i', int(coord.shape[0]))) 
    for iy, ix in np.ndindex(coord.shape):
        curr_coordinate = int(np.round(coord[iy, ix],2)*100);
        asocket.send(pack('i', curr_coordinate)) 
        print("[" + str(iy) + "," + str(ix) + "]: " + str(coord[iy, ix]) +" -> " + str(curr_coordinate))


def update_image(frame, w_gui_img, h_gui_img):
    # Update image in GUI
    frame = cv2.resize(frame, (w_gui_img, h_gui_img))
    imgbytes = cv2.imencode(".ppm", frame)[1].tobytes()
    a_id = graph_elem.draw_image(data=imgbytes, location=(0, 0))
    graph_elem.send_figure_to_back(a_id)
    return a_id

if __name__ == "__main__":
    w, h = 2448, 2048 # size of the input image
    w_gui, h_gui = 700, 900 # size of the GUI window
    w_gui_img, h_gui_img = 612, 512 # size of the image in GUI window
    w_path = os.path.dirname(os.path.realpath(__file__))
    os.chdir(w_path)
    os.makedirs("background", exist_ok=True)
    os.makedirs("textiles", exist_ok=True)
    os.makedirs("coordinates", exist_ok=True)
    os.makedirs("log", exist_ok=True)

    with open("calibration_matrix.yaml", "r") as f:
        camera_dict = yaml.safe_load(f)

    sg.theme("Black")

    column = [[sg.Graph((w_gui_img, h_gui_img), (0, h_gui_img), (w_gui_img, 0), 
                        key="-GRAPH-", enable_events=True, drag_submits=True)]]
    column2 = [[sg.Text("SAMPLE: ", font=("Arial", 16, "bold"), key="-SAMPLE TEXT-")],
               [sg.Text("Enter Sample Name: ", font=("Arial", 13)), 
                sg.InputText(size=(30,1),key="-SAMPLE-"),
               sg.Button("SUBMIT", size=(15, 1), key="-SAMPLE KEY-", bind_return_key=True)],
               [sg.Button("CAPTURE BACKGROUND", size=(26, 1), key="-BACKGROUND-", disabled=True),
                sg.Button("SHOW BACKGROUND IMG", size=(26, 1), key="-SHOW BACKGROUND-", disabled=True)],
               [sg.Button("CAPTURE TEXTILE", size=(26, 1), key="-TEXTILE-", disabled=True),
                sg.Button("SHOW TEXTILE IMG", size=(26, 1), key="-SHOW TEXTILE-", disabled=True)],
               [sg.Button("SHOW MASK IMG", size=(26, 1), key="-SHOW MASK-", disabled=True)],
               [sg.Text("Spacing:\t", font=("Arial", 13)),
                sg.Slider((10, 100), 20, 10, font=("Arial", 12), orientation="h",
                   size=(40, 15), key="-SPACING-")],
               [sg.Text("Dilation:\t", font=("Arial", 13)),
                sg.Slider((1, 255), 1, 1, font=("Arial", 12), orientation="h",
                   size=(40, 15), key="-DILATION-")],
               [sg.Text("Thresh:\t", font=("Arial", 13)),
                sg.Slider((1, 255), 50, 1, font=("Arial", 12), orientation="h",
                   size=(40, 15), key="-BG THRESH-")],
               [sg.Button("DRAW PATH", size=(26, 1), key="-DRAW GRID-", disabled=True),
               sg.Button("SEND COORDINATES", size=(26, 1), key="-NEXT-", disabled=True)]]#,
#               [sg.Text("Coordinates: ", font=("Arial", 13)), 
#                sg.InputText(size=(15,1),key="-X-"), sg.InputText(size=(15,1),key="-Y-")],
#               [sg.Button("SEND COORDINATE", size=(26, 1), key="-SEND COORD-", disabled=False)]]
    layout = [[sg.Column(column2)],
              [sg.Column(column, size=(w_gui, h_gui), scrollable=True, key="-COLUMN-")]]

    window = sg.Window("EnzaTex", layout, use_default_focus=False,
                       resizable=True, size=(w_gui, h_gui), finalize=True)
    graph_elem = window["-GRAPH-"]
    a_id = None

    cam = Camera()

    img = np.zeros((w, h, 3))
    img_bg = np.zeros((w, h, 3))
    a_id = update_image(img, w_gui_img, h_gui_img)
    bg_flag, textile_flag = False, False
    now = datetime.now().strftime("%Y-%m-%d_%H-%M")
    csvfile = open(os.path.join("log", "log_"+now+".csv"),"w", newline="")
    log = csv.writer(csvfile, delimiter=",", quotechar="|", quoting=csv.QUOTE_MINIMAL)
    log.writerow(["Sample Name", "Timestamp", "Spacing", "Dilation", "Background Threshold"])
    
    mtx = np.asarray(camera_dict["camera_matrix"])
    dist = np.asarray(camera_dict["dist_coeff"])
    newcameramtx, roi = cv2.getOptimalNewCameraMatrix(mtx, dist, (w,h), 1, (w,h))
    
    while True:
        event, values = window.read(timeout=0)
        if event in ("Exit", None):
            window.close()
            break
#        if event == "-SEND COORD-":
#            coord = np.asarray([values["-X-"], values["-Y-"]]).reshape((1,2))
#            coord = pixel2world(coord, camera_dict)
#            asocket = socket_to_automat(TCP_IP, TCP_PORT, True)
#            sample = "0";
#            send_to_socket(asocket, sample, coord)
#            asocket.close()

        if event == "-SAMPLE KEY-":
            if values["-SAMPLE-"] != "":
                sample = values["-SAMPLE-"]
                window["-TEXTILE-"].update(disabled=False)
                window["-BACKGROUND-"].update(disabled=False)
                window["-SAMPLE TEXT-"].update("SAMPLE: {}".format(sample))
                if img_bg.sum()>0:
                    window["-SHOW BACKGROUND-"].update(disabled=False)

        if event == "-BACKGROUND-":
            img_bg = cam.capture()
            graph_elem.delete_figure(a_id)
            a_id = update_image(img_bg, w_gui_img, h_gui_img)
            bg_flag = True
            window["-SHOW BACKGROUND-"].update(disabled=False)

        if event == "-TEXTILE-":
            img = cam.capture()
            graph_elem.delete_figure(a_id)
            a_id = update_image(img, w_gui_img, h_gui_img)
            textile_flag = True
            window["-SHOW TEXTILE-"].update(disabled=False)

        if event == "-SHOW BACKGROUND-":
            graph_elem.delete_figure(a_id)
            a_id = update_image(img_bg, w_gui_img, h_gui_img)

        if event == "-SHOW TEXTILE-":
            graph_elem.delete_figure(a_id)
            a_id = update_image(img, w_gui_img, h_gui_img)
            
        if event == "-SHOW MASK-":
            graph_elem.delete_figure(a_id)
            if len(img_mask.shape)==2:
                img_mask = cv2.cvtColor(img_mask, cv2.COLOR_GRAY2BGR)
            a_id = update_image(img_mask, w_gui_img, h_gui_img)

        if textile_flag and bg_flag:
            window["-DRAW GRID-"].update(disabled=False)

        if event == "-NEXT-":
            asocket = socket_to_automat(TCP_IP, TCP_PORT, True)
            send_to_socket(asocket, sample, world_coords)
            asocket.close()
            log.writerow([sample, datetime.now(), values["-SPACING-"], 
                          values["-DILATION-"], values["-BG THRESH-"]])
            csvfile.flush()
            window["-NEXT-"].update(disabled=True)
            window["-TEXTILE-"].update(disabled=True)
            window["-DRAW GRID-"].update(disabled=True)
            window["-BACKGROUND-"].update(disabled=True)
            window["-SHOW TEXTILE-"].update(disabled=True)
            window["-SHOW BACKGROUND-"].update(disabled=True)
            window["-SAMPLE TEXT-"].update("SAMPLE: ")
            window["-SAMPLE-"].update("")
            window["-SHOW MASK-"].update(disabled=True)
            textile_flag = False
            img = np.zeros((w, h, 3))
            graph_elem.delete_figure(a_id)
            sample = ""
            
        if event == "-DRAW GRID-":
            try:
                vis_img, world_coords, img_mask = path_generation(
                camera_dict, img, img_bg, spacing=values["-SPACING-"], 
                dilation=values["-DILATION-"], bg_thresh=values["-BG THRESH-"])
            except:
                print("Path Generation Failed")
                continue
            graph_elem.delete_figure(a_id)
            a_id = update_image(vis_img, w_gui_img, h_gui_img)
            window["-NEXT-"].update(disabled=False)
            coord_filename = os.path.join("coordinates", sample + ".txt")
            cv2.imwrite(os.path.join("background", sample + ".png"), img_bg)
            cv2.imwrite(os.path.join("textiles", sample + ".png"), img)
            np.savetxt(coord_filename, world_coords, fmt="%10.5f")
            window["-SHOW MASK-"].update(disabled=False)


    csvfile.close()  
    cam.destroy()
    window.close()
