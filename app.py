import streamlit as st
import cv2
import torch
from utils.hubconf import custom
from utils.plots import plot_one_box
import numpy as np
import tempfile
from PIL import ImageColor
import time
from collections import Counter
import json
import psutil
import subprocess
import pandas as pd
import random
import base64

# 사이드바, 기본 배경
# def add_bg_from_local(image_file):
#     with open(image_file, "rb") as image_file:
#         encoded_string = base64.b64encode(image_file.read())
#     st.markdown(
#         f"""
#     <style>
#     .stApp {{
#         background-image: url(data:image/{"mp4"};base64,{encoded_string.decode()});
#         background-size: cover
#     }}
#     </style>
#     """,
#         unsafe_allow_html=True
#     )
# def sidebar_bg(side_bg):
#
#    side_bg_ext = 'png'
#
#    st.markdown(
#       f"""
#       <style>
#       [data-testid="stSidebar"] > div:first-child {{
#           background: url(data:image/{side_bg_ext};base64,{base64.b64encode(open(side_bg, "rb").read()).decode()});
#       }}
#       </style>
#       """,
#       unsafe_allow_html=True,
#       )
#
# side_bg = 'logo.jpg'
# sidebar_bg(side_bg)
# add_bg_from_local('example.jpg')

# 비디오 배경
# video_html = """
# 		<style>
#
# 		#myVideo {
# 		  position: fixed;
# 		  right: 0;
# 		  bottom: 0;
# 		  min-width: 100%;
# 		  min-height: 100%;
# 		}
#
# 		.content {
# 		  position: fixed;
# 		  bottom: 0;
# 		  background: rgba(0, 0, 0, 0.5);
# 		  color: #f1f1f1;
# 		  width: 100%;
# 		  padding: 20px;
# 		}
#
# 		</style>
# 		<video autoplay muted loop id="myVideo">
# 		  <source src="https://pixabay.com/videos/id-142579/")>
#
# 		</video>
#         """
#
# st.markdown(video_html, unsafe_allow_html=True)



def get_gpu_memory():
    result = subprocess.check_output(
        [
            'nvidia-smi', '--query-gpu=memory.used',
            '--format=csv,nounits,noheader'
        ], encoding='utf-8')
    gpu_memory = [int(x) for x in result.strip().split('\n')]
    return gpu_memory[0]

def random_color():
    return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

def color_picker_fn(classname, key):
    color_picke = st.sidebar.color_picker(f'{classname}:', '#00FFAA', key=key)
    color_rgb_list = list(ImageColor.getcolor(str(color_picke), "RGB"))
    color = [color_rgb_list[2], color_rgb_list[1], color_rgb_list[0]]
    return color

p_time = 0

st.title('Yolov7 - 차량인식 프로젝트')
sample_img = cv2.imread("cctv.jpg")
FRAME_WINDOW = st.image(sample_img, channels='BGR')
st.sidebar.title('Settings')

# 가중치 적용 - 가중치 주소 값 입력
path_model_file = 'C:/Users/zerobig/PycharmProjects/streamlit-yolov7/best_e6.pt'

# 클래스 적용 - class.txt 수정
path_to_class_file = 'C:/Users/zerobig/PycharmProjects/yolov7_streamlit/class.txt'
with open(path_to_class_file) as f:
    path_to_class_txt = f.read().splitlines()

if path_to_class_txt is not None:

    options = st.sidebar.radio(
        'Options:', ('Webcam', 'Image', 'Video'), index=1)

    gpu_option = st.sidebar.radio(
        'PU Options:', ('CPU', 'GPU'))

    if not torch.cuda.is_available():
        st.sidebar.warning('CPU만 사용가능합니다.', icon="⚠️")
    else:
        st.sidebar.success(
            'GPU 사용가능합니다.',
            icon="✅"
        )

    # Confidence
    confidence = st.sidebar.slider(
        'Detection Confidence', min_value=0.01, max_value=1.0, value=0.01)

    # Draw thickness
    draw_thick = st.sidebar.slider(
        'Draw Thickness:', min_value=1,
        max_value=20, value=3
    )

    # read class.txt
    class_labels = path_to_class_txt
    color_pick_list = []

    for i in range(len(class_labels)):
        classname = class_labels[i]
        color = color_picker_fn(classname, i)
        color_pick_list.append(color)

    # Image
    if options == 'Image':
        upload_img_file = st.sidebar.file_uploader(
            'Upload Image', type=['jpg', 'jpeg', 'png'])
        if upload_img_file is not None:
            pred = st.button('Predict Using YOLOv7')
            file_bytes = np.asarray(
                bytearray(upload_img_file.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, 1)
            FRAME_WINDOW.image(img, channels='BGR')

            if pred:
                if gpu_option == 'CPU':
                    model = custom(path_or_model=path_model_file)
                if gpu_option == 'GPU':
                    model = custom(path_or_model=path_model_file, gpu=True)

                bbox_list = []
                current_no_class = []
                results = model(img)

                # Bounding Box
                box = results.pandas().xyxy[0]
                class_list = box['class'].to_list()

                for i in box.index:
                    xmin, ymin, xmax, ymax, conf = int(box['xmin'][i]), int(box['ymin'][i]), int(box['xmax'][i]), \
                                                   int(box['ymax'][i]), box['confidence'][i]
                    if conf > confidence:
                        bbox_list.append([xmin, ymin, xmax, ymax])
                if len(bbox_list) != 0:
                    for bbox, id in zip(bbox_list, class_list):
                        plot_one_box(bbox, img, label=class_labels[id],
                                     color=color_pick_list[id], line_thickness=draw_thick)
                        current_no_class.append([class_labels[id]])
                FRAME_WINDOW.image(img, channels='BGR')

                # Current number of classes
                class_fq = dict(Counter(i for sub in current_no_class for i in set(sub)))
                class_fq = json.dumps(class_fq, indent=4)
                class_fq = json.loads(class_fq)
                df_fq = pd.DataFrame(class_fq.items(), columns=['Class', 'Number'])

                # Updating Inference results
                with st.container():
                    st.markdown("<h2>Inference Statistics</h2>", unsafe_allow_html=True)
                    st.markdown("<h3>Detected objects in curret Frame</h3>", unsafe_allow_html=True)
                    st.dataframe(df_fq, use_container_width=True)

    # Video
    if options == 'Video':
        upload_video_file = st.sidebar.file_uploader(
            'Upload Video', type=['mp4', 'avi', 'mkv'])
        if upload_video_file is not None:
            pred = st.checkbox('Predict Using YOLOv7')
            # Model
            if gpu_option == 'CPU':
                model = custom(path_or_model=path_model_file)
            if gpu_option == 'GPU':
                model = custom(path_or_model=path_model_file, gpu=True)

            tfile = tempfile.NamedTemporaryFile(delete=False)
            tfile.write(upload_video_file.read())
            cap = cv2.VideoCapture(tfile.name)
            if pred:
                FRAME_WINDOW.image([])
                stframe1 = st.empty()
                stframe2 = st.empty()
                stframe3 = st.empty()
                while True:
                    success, img = cap.read()
                    if not success:
                        st.error(
                            'Video file NOT working\n \
                            Check Video path or file properly!!',
                            icon="🚨"
                        )
                        break
                    current_no_class = []
                    bbox_list = []
                    results = model(img)
                    # Bounding Box
                    box = results.pandas().xyxy[0]
                    class_list = box['class'].to_list()

                    for i in box.index:
                        xmin, ymin, xmax, ymax, conf = int(box['xmin'][i]), int(box['ymin'][i]), int(box['xmax'][i]), \
                                                       int(box['ymax'][i]), box['confidence'][i]
                        if conf > confidence:
                            bbox_list.append([xmin, ymin, xmax, ymax])
                    if len(bbox_list) != 0:
                        for bbox, id in zip(bbox_list, class_list):
                            plot_one_box(bbox, img, label=class_labels[id],
                                         color=color_pick_list[id], line_thickness=draw_thick)
                            current_no_class.append([class_labels[id]])
                    FRAME_WINDOW.image(img, channels='BGR')

                    # FPS
                    c_time = time.time()
                    fps = 1 / (c_time - p_time)
                    p_time = c_time

                    # Current number of classes
                    class_fq = dict(Counter(i for sub in current_no_class for i in set(sub)))
                    class_fq = json.dumps(class_fq, indent=4)
                    class_fq = json.loads(class_fq)
                    df_fq = pd.DataFrame(class_fq.items(), columns=['Class', 'Number'])

                    # Updating Inference results
                    with stframe1.container():
                        st.markdown("<h2>Inference Statistics</h2>", unsafe_allow_html=True)
                        if round(fps, 4) > 1:
                            st.markdown(f"<h4 style='color:green;'>Frame Rate: {round(fps, 4)}</h4>",
                                        unsafe_allow_html=True)
                        else:
                            st.markdown(f"<h4 style='color:red;'>Frame Rate: {round(fps, 4)}</h4>",
                                        unsafe_allow_html=True)

                    with stframe2.container():
                        st.markdown("<h3>Detected objects in curret Frame</h3>", unsafe_allow_html=True)
                        st.dataframe(df_fq, use_container_width=True)

                    with stframe3.container():
                        st.markdown("<h2>System Statistics</h2>", unsafe_allow_html=True)
                        js1, js2, js3 = st.columns(3)

                        # Updating System stats
                        with js1:
                            st.markdown("<h4>Memory usage</h4>", unsafe_allow_html=True)
                            mem_use = psutil.virtual_memory()[2]
                            if mem_use > 50:
                                js1_text = st.markdown(f"<h5 style='color:red;'>{mem_use}%</h5>",
                                                       unsafe_allow_html=True)
                            else:
                                js1_text = st.markdown(f"<h5 style='color:green;'>{mem_use}%</h5>",
                                                       unsafe_allow_html=True)

                        with js2:
                            st.markdown("<h4>CPU Usage</h4>", unsafe_allow_html=True)
                            cpu_use = psutil.cpu_percent()
                            if mem_use > 50:
                                js2_text = st.markdown(f"<h5 style='color:red;'>{cpu_use}%</h5>",
                                                       unsafe_allow_html=True)
                            else:
                                js2_text = st.markdown(f"<h5 style='color:green;'>{cpu_use}%</h5>",
                                                       unsafe_allow_html=True)

                        with js3:
                            st.markdown("<h4>GPU Memory Usage</h4>", unsafe_allow_html=True)
                            try:
                                js3_text = st.markdown(f'<h5>{get_gpu_memory()} MB</h5>', unsafe_allow_html=True)
                            except:
                                js3_text = st.markdown('<h5>NA</h5>', unsafe_allow_html=True)

    # Web-cam
    if options == 'Webcam':
        cam_options = st.sidebar.selectbox('Webcam Channel',
                                           ('Select Channel', '0', '1', '2', '3'))
        # Model
        if gpu_option == 'CPU':
            model = custom(path_or_model=path_model_file)
        if gpu_option == 'GPU':
            model = custom(path_or_model=path_model_file, gpu=True)

        if len(cam_options) != 0:
            if not cam_options == 'Select Channel':
                cap = cv2.VideoCapture(int(cam_options))
                stframe1 = st.empty()
                stframe2 = st.empty()
                stframe3 = st.empty()
                while True:
                    success, img = cap.read()
                    if not success:
                        st.error(
                            f'Webcam channel {cam_options} NOT working\n \
                            Change channel or Connect webcam properly!!',
                            icon="🚨"
                        )
                        break

                    bbox_list = []
                    current_no_class = []
                    results = model(img)

                    # Bounding Box
                    box = results.pandas().xyxy[0]
                    class_list = box['class'].to_list()

                    for i in box.index:
                        xmin, ymin, xmax, ymax, conf = int(box['xmin'][i]), int(box['ymin'][i]), int(box['xmax'][i]), \
                                                       int(box['ymax'][i]), box['confidence'][i]
                        if conf > confidence:
                            bbox_list.append([xmin, ymin, xmax, ymax])
                    if len(bbox_list) != 0:
                        for bbox, id in zip(bbox_list, class_list):
                            plot_one_box(bbox, img, label=class_labels[id],
                                         color=color_pick_list[id], line_thickness=draw_thick)
                            current_no_class.append([class_labels[id]])
                    FRAME_WINDOW.image(img, channels='BGR')

                    # FPS
                    c_time = time.time()
                    fps = 1 / (c_time - p_time)
                    p_time = c_time

                    # Current number of classes
                    class_fq = dict(Counter(i for sub in current_no_class for i in set(sub)))
                    class_fq = json.dumps(class_fq, indent=4)
                    class_fq = json.loads(class_fq)
                    df_fq = pd.DataFrame(class_fq.items(), columns=['Class', 'Number'])

                    # Updating Inference results
                    with stframe1.container():
                        st.markdown("<h2>Inference Statistics</h2>", unsafe_allow_html=True)
                        if round(fps, 4) > 1:
                            st.markdown(f"<h4 style='color:green;'>Frame Rate: {round(fps, 4)}</h4>",
                                        unsafe_allow_html=True)
                        else:
                            st.markdown(f"<h4 style='color:red;'>Frame Rate: {round(fps, 4)}</h4>",
                                        unsafe_allow_html=True)

                    with stframe2.container():
                        st.markdown("<h3>Detected objects in curret Frame</h3>", unsafe_allow_html=True)
                        st.dataframe(df_fq, use_container_width=True)

                    with stframe3.container():
                        st.markdown("<h2>System Statistics</h2>", unsafe_allow_html=True)
                        js1, js2, js3 = st.columns(3)

                        # Updating System stats
                        with js1:
                            st.markdown("<h4>Memory usage</h4>", unsafe_allow_html=True)
                            mem_use = psutil.virtual_memory()[2]
                            if mem_use > 50:
                                js1_text = st.markdown(f"<h5 style='color:red;'>{mem_use}%</h5>",
                                                       unsafe_allow_html=True)
                            else:
                                js1_text = st.markdown(f"<h5 style='color:green;'>{mem_use}%</h5>",
                                                       unsafe_allow_html=True)

                        with js2:
                            st.markdown("<h4>CPU Usage</h4>", unsafe_allow_html=True)
                            cpu_use = psutil.cpu_percent()
                            if mem_use > 50:
                                js2_text = st.markdown(f"<h5 style='color:red;'>{cpu_use}%</h5>",
                                                       unsafe_allow_html=True)
                            else:
                                js2_text = st.markdown(f"<h5 style='color:green;'>{cpu_use}%</h5>",
                                                       unsafe_allow_html=True)

                        with js3:
                            st.markdown("<h4>GPU Memory Usage</h4>", unsafe_allow_html=True)
                            try:
                                js3_text = st.markdown(f'<h5>{get_gpu_memory()} MB</h5>', unsafe_allow_html=True)
                            except:
                                js3_text = st.markdown('<h5>NA</h5>', unsafe_allow_html=True)

    # RTSP
    # if options == 'RTSP':
    #     rtsp_url = st.sidebar.text_input(
    #         'RTSP URL:',
    #         'eg: rtsp://admin:name6666@198.162.1.58/cam/realmonitor?channel=0&subtype=0'
    #     )
    #     # st.sidebar.markdown('Press Enter after pasting RTSP URL')
    #     url = rtsp_url[:-11]
    #     rtsp_options = st.sidebar.selectbox(
    #         'RTSP Channel',
    #         ('Select Channel', '0', '1', '2', '3',
    #          '4', '5', '6', '7', '8', '9', '10')
    #     )
    #
    #     # Model
    #     if gpu_option == 'CPU':
    #         model = custom(path_or_model=path_model_file)
    #     if gpu_option == 'GPU':
    #         model = custom(path_or_model=path_model_file, gpu=True)
    #
    #     if not rtsp_options == 'Select Channel':
    #         cap = cv2.VideoCapture(f'{url}{rtsp_options}&subtype=0')
    #         stframe1 = st.empty()
    #         stframe2 = st.empty()
    #         stframe3 = st.empty()
    #         while True:
    #             success, img = cap.read()
    #             if not success:
    #                 st.error(
    #                     f'RSTP channel {rtsp_options} NOT working\nChange channel or Connect properly!!',
    #                     icon="🚨"
    #                 )
    #                 break
    #
    #             bbox_list = []
    #             current_no_class = []
    #             results = model(img)
    #
    #             # Bounding Box
    #             box = results.pandas().xyxy[0]
    #             class_list = box['class'].to_list()
    #
    #             for i in box.index:
    #                 xmin, ymin, xmax, ymax, conf = int(box['xmin'][i]), int(box['ymin'][i]), int(box['xmax'][i]), \
    #                                                int(box['ymax'][i]), box['confidence'][i]
    #                 if conf > confidence:
    #                     bbox_list.append([xmin, ymin, xmax, ymax])
    #             if len(bbox_list) != 0:
    #                 for bbox, id in zip(bbox_list, class_list):
    #                     plot_one_box(bbox, img, label=class_labels[id],
    #                                  color=color_pick_list[id], line_thickness=draw_thick)
    #                     current_no_class.append([class_labels[id]])
    #             FRAME_WINDOW.image(img, channels='BGR')
    #
    #             # FPS
    #             c_time = time.time()
    #             fps = 1 / (c_time - p_time)
    #             p_time = c_time
    #
    #             # Current number of classes
    #             class_fq = dict(Counter(i for sub in current_no_class for i in set(sub)))
    #             class_fq = json.dumps(class_fq, indent=4)
    #             class_fq = json.loads(class_fq)
    #             df_fq = pd.DataFrame(class_fq.items(), columns=['Class', 'Number'])
    #
    #             # Updating Inference results
    #             with stframe1.container():
    #                 st.markdown("<h2>Inference Statistics</h2>", unsafe_allow_html=True)
    #                 if round(fps, 4) > 1:
    #                     st.markdown(f"<h4 style='color:green;'>Frame Rate: {round(fps, 4)}</h4>",
    #                                 unsafe_allow_html=True)
    #                 else:
    #                     st.markdown(f"<h4 style='color:red;'>Frame Rate: {round(fps, 4)}</h4>", unsafe_allow_html=True)
    #
    #             with stframe2.container():
    #                 st.markdown("<h3>Detected objects in curret Frame</h3>", unsafe_allow_html=True)
    #                 st.dataframe(df_fq, use_container_width=True)
    #
    #             with stframe3.container():
    #                 st.markdown("<h2>System Statistics</h2>", unsafe_allow_html=True)
    #                 js1, js2, js3 = st.columns(3)
    #
    #                 # Updating System stats
    #                 with js1:
    #                     st.markdown("<h4>Memory usage</h4>", unsafe_allow_html=True)
    #                     mem_use = psutil.virtual_memory()[2]
    #                     if mem_use > 50:
    #                         js1_text = st.markdown(f"<h5 style='color:red;'>{mem_use}%</h5>", unsafe_allow_html=True)
    #                     else:
    #                         js1_text = st.markdown(f"<h5 style='color:green;'>{mem_use}%</h5>", unsafe_allow_html=True)
    #
    #                 with js2:
    #                     st.markdown("<h4>CPU Usage</h4>", unsafe_allow_html=True)
    #                     cpu_use = psutil.cpu_percent()
    #                     if mem_use > 50:
    #                         js2_text = st.markdown(f"<h5 style='color:red;'>{cpu_use}%</h5>", unsafe_allow_html=True)
    #                     else:
    #                         js2_text = st.markdown(f"<h5 style='color:green;'>{cpu_use}%</h5>", unsafe_allow_html=True)
    #
    #                 with js3:
    #                     st.markdown("<h4>GPU Memory Usage</h4>", unsafe_allow_html=True)
    #                     try:
    #                         js3_text = st.markdown(f'<h5>{get_gpu_memory()} MB</h5>', unsafe_allow_html=True)
    #                     except:
    #                         js3_text = st.markdown('<h5>NA</h5>', unsafe_allow_html=True)