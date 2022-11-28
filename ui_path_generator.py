import yaml
import os
import glob
import cv2
import PySimpleGUI as sg
import numpy as np
from path_generator import path_generation

def update_image(frame, w_gui, h_gui):
    frame = cv2.resize(frame, (w_gui, h_gui))

    # on some ports, will need to change to png
    imgbytes = cv2.imencode('.ppm', frame)[1].tobytes()
    a_id = graph_elem.draw_image(
        data=imgbytes, location=(
            0, 0))    # draw new image
    graph_elem.send_figure_to_back(a_id)
    return a_id

if __name__ == "__main__":
    w, h = 2448, 2048
    w_gui, h_gui = 612, 512
    
    textile_img_path = os.path.normpath("textiles")
    img_paths = sorted(glob.glob(textile_img_path + "/*.bmp"))
    img_bg = cv2.imread("background/2000.bmp")
    with open("calibration_matrix.yaml", "r") as f:
        camera_dict = yaml.safe_load(f)

    sg.theme("Black")

    column = [[sg.Graph((w_gui, h_gui), (0, h_gui), (w_gui, 0), key='-GRAPH-',
                        enable_events=True, drag_submits=True)]]
    column2 = [[sg.Text("Spacing:\t", font=('Arial', 13)),
            sg.Slider(
                (1, 255),
                25,
                1, font=('Arial', 12),
                orientation="h",
                size=(40, 15),
                key="-SPACING-")],
            [sg.Text("Dilation:\t", font=('Arial', 13)),
            sg.Slider(
                (1, 255),
                25,
                1, font=('Arial', 12),
                orientation="h",
                size=(40, 15),
                key="-DILATION-")],
                [sg.Button("DRAW PATH", size=(26, 1), key="-DRAW GRID-")],  # ,
                [sg.Button("SAVE & NEXT", size=(26, 1), key="-NEXT-", disabled=True)]]
    layout = [[sg.Column(column2)],
            [sg.Column(column, size=(w + 10, h + 10), scrollable=True, key="-COLUMN-")]]

    window = sg.Window( 'EnzaTex', layout, 
                    resizable=True, size=(800, 800), finalize=True)
    graph_elem = window['-GRAPH-']      # type: sg.Graph
    a_id = None

    for i in range(len(img_paths)):
        img_path = img_paths[i]
        img = cv2.imread(img_path)
        
        if a_id is not None:
            graph_elem.delete_figure(a_id)
        a_id = update_image(img, w_gui, h_gui)
        
        if i == len(img_paths)-1:
            window['-NEXT-'].update("SAVE & CLOSE")
        
        while True:
            event, values = window.read(timeout=0)
            if event in ('Exit', None):
                window.close()
                exit()
            
            if event == "-NEXT-":
                filename = os.path.basename(img_path).replace(".bmp", ".txt")
                np.savetxt(filename, world_coords, fmt='%10.5f')
                print("Saved Coordinates to {}".format(filename))
                window["-NEXT-"].update(disabled=True)
                break
                
            if event == "-DRAW GRID-":
                vis_img, world_coords = path_generation(camera_dict, img, img_bg, spacing=values["-SPACING-"], dilation=values["-DILATION-"])
                graph_elem.delete_figure(a_id)
                a_id = update_image(vis_img, w_gui, h_gui)
                window['-NEXT-'].update(disabled=False)           

    window.close()