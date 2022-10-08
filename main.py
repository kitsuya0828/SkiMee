import PySimpleGUI as sg
import cv2
import pyocr
import datetime
import numpy as np
import pyautogui as gui
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from PIL import Image
from time import sleep
import io
import os
import sys

# Tesseract のモジュールを格納するフォルダ
RESORSES_FOLDER_NAME = 'Tesseract' 
# Tesseract-OCRのパスを環境変数「PATH」へ追記する
os.environ["PATH"] += os.pathsep + os.path.dirname(os.path.abspath(__file__)) + os.sep + RESORSES_FOLDER_NAME


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def ocr_binarized_image(image_path, threshold=0, threshold_type=cv2.THRESH_BINARY):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    ret, img_thresh = cv2.threshold(img, threshold, 255, threshold_type)
    # print(f"ret:{ret}")
    img2 = cv2.bitwise_not(img_thresh)
    thresh_path = image_path
    cv2.imwrite(thresh_path, img2)

    tools = pyocr.get_available_tools()
    if len(tools) == 0:
        print("No OCR tool found")
        sys.exit(1)
    tool = tools[0]
    # print("Will use tool '%s'" % (tool.get_name()))

    str_num = tool.image_to_string(
        Image.open(thresh_path),
        lang='eng',
        builder = pyocr.builders.TextBuilder(tesseract_layout = 6)
    )
    return int(str_num)


# ボタン押下により会議を退出する関数
def leave_meeting(image_path, app):
    X,Y = gui.locateCenterOnScreen(image_path, confidence=0.9)
    gui.moveTo(X,Y)
    if app == 'Google Meet':
        gui.doubleClick(X,Y)
    elif app == 'Zoom':
        gui.click(X,Y)
        gui.press('enter')

x = []
y = []
exit_cnt = 0
max_num = 0

def make_data_fig():
    global x,y
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.set_xlabel('Time')
    ax.set_ylabel('Number of People')
    ax.yaxis.set_major_locator(MultipleLocator(1))
    ax.grid(color='black', linestyle=':', linewidth=0.3, alpha=0.5)
    ax.set_title('Real-Time Line Graph')
    ax.plot(x, y, marker='.')
    return fig

def draw_plot_image(fig):
    item = io.BytesIO()
    plt.savefig(item, format='png')
    plt.clf()
    return item.getvalue()


def display_main(participant_path, exit_path, alpha, app, denominator, times):
    global x,y,max_num,exit_cnt
    layout = [[sg.Checkbox('グラフ表示',key='-display-', default=True)],
                [sg.Image(filename='', key='-image-')],
                [sg.Text('繰り返し間隔（s）:', size=(20,1)), sg.Slider((0,10), default_value=0, orientation='h', key='-delay-')],
                [sg.Button('終了'), sg.Button('ホーム')], 
                ]

    window = sg.Window('SkiMee 【 リアルタイムビュー 】', layout=layout,  font='メイリオ', alpha_channel=alpha, icon=resource_path('SkiMee.ico'))

    while True:
        event, values = window.read(timeout=0)
        if event in (None, '終了'):
            break
        elif event == 'ホーム':
            window.close()
            return True

        try:
            X,Y,W,H = gui.locateOnScreen(participant_path, confidence=0.8)
            if app == 'Google Meet':
                cropped_img = gui.screenshot(region=(X+W/2,Y-2*H/3,W,2*H/3))
            elif app == 'Zoom':
                cropped_img = gui.screenshot(region=(X+W,Y,2*W/3,4*H/5))
            cropped_img.save('.\\sankasha.png')
            num = ocr_binarized_image('.\\sankasha.png',127,cv2.THRESH_BINARY)

            if num:
                if num < max_num/denominator:
                    exit_cnt += 1
                elif exit_cnt > 0:
                    exit_cnt = 0

                max_num = max(num, max_num)
                x.append(datetime.datetime.now())
                y.append(num)

        except Exception as e:
            print(e)

        if values['-display-']:
            fig_ = make_data_fig()
            fig_bytes = draw_plot_image(fig_)
            window['-image-'].update(data=fig_bytes)
        else:
            window['-image-'].update(filename='')

        if exit_cnt >= times:
            exit_cnt = 0
            leave_meeting(exit_path, app)
            break
        sleep(values['-delay-'])

    window.close()


# ステップ2. デザインテーマの設定
sg.theme('BlueMono')

# ステップ3. ウィンドウの部品とレイアウト
layout = [
    [sg.Text('※ Zoom / Google Meet の「参加者数アイコン」と「退出ボタン」のスクリーンショットを撮ってアップロードしてください。')],
    [sg.Text('▶ 使用するオンライン会議アプリを選択：'), sg.Combo(('Google Meet', 'Zoom'), default_value='Google Meet', key='-app-'), sg.Button('更新', key='-refresh-')],
    [sg.Text('Google Meet の場合は、スクリーンショット時に Chrome のズームを 200% にするのがオススメです。', key='-caution-')],
    [sg.Text('▼ アップロード画像(1) 参加者数アイコン'), sg.Text('※ ファイルパスに日本語を含まないようにしてください', text_color='#ff0000')],
    [sg.Image(filename=resource_path('images/406-203.png'), size=(406,203), key='-img1-')],
    [sg.Input(), sg.FileBrowse('ファイルを選択', key='inputFilePath1')],
    [sg.Text('▼ アップロード画像(2) 退出ボタン'), sg.Text('※ ファイルパスに日本語を含まないようにしてください', text_color='#ff0000')],
    [sg.Image(filename=resource_path('images/239-203.png'), size=(239,203), key='-img2-')],
    [sg.Input(), sg.FileBrowse('ファイルを選択', key='inputFilePath2')],
    [sg.Text('▶ ウィンドウ不透明度(0=非表示,1=完全に表示)：'), sg.Slider((0.0,1.0), default_value=1.0, resolution=0.1, orientation='h', key='-alpha-')],
    [sg.Text('▶ 自動退出する条件を選択：'), sg.Text('最大参加人数の'), sg.Combo(('1/2未満 ','1/3未満 '), default_value='1/2未満 ', key='-denominator-'), sg.Text('が'), sg.Combo(('1回連続 ','2回連続 ','3回連続 '), default_value='2回連続 ', key='-times-')],
    [sg.Button('はじめる', key='-start-')],
]

# ステップ4. ウィンドウの生成
window = sg.Window('SkiMee 【 自動退出支援プログラム 】', layout=layout, font='メイリオ', icon=resource_path('images/SkiMee.ico'))

# ステップ5. イベントループ
while True:
    event, values = window.read()

    if event == '-refresh-':
        if values['-app-'] == 'Zoom':
            window['-caution-'].update('Zoom の場合は、全画面表示にするのがオススメです。')
            window['-img1-'].update(filename=resource_path('images/591-203.png'))
            window['-img2-'].update(filename=resource_path('images/332-203.png'))
        elif values['-app-'] == 'Google Meet':
            window['-caution-'].update('Google Meet の場合は、スクリーンショット時に Chrome のズームを 200% にするのがオススメです。')
            window['-img1-'].update(filename=resource_path('images/406-203.png'))
            window['-img2-'].update(filename=resource_path('images/239-203.png'))

    if event == sg.WIN_CLOSED:
        break

    elif event == "-start-":
        denominator = 2 if values['-denominator-'].startswith('1/2') else 3
        times = 2 if values['-times-'].startswith('2') else 3

        window.Hide() # アップロード画面を隠す
        # メイン画面を表示する
        main_return = display_main(values['inputFilePath1'], values['inputFilePath2'], values['-alpha-'], values['-app-'], denominator, times)
        # もしNoneが返ってきたらアップロード画面も終了させる
        if main_return is None:
            break
        elif main_return == True:
            window.UnHide() # アップロード画面を再表示する

window.close()