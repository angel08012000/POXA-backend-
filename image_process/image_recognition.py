import cv2, json, datetime, sys, os, re, ast
import numpy as np
import pathlib

from collections import defaultdict
from google import genai
from google.genai import types
from typing import Tuple

from image_processing import get_line_graphs_by_title, get_filtered_lines

GEMINI_API_KEY = "AIzaSyAsO1xPnKc6YDfA3C01fEuG3-wF_7rEWEM"

# 一次傳多張圖
def get_line_graph_y_value_ai_v2(img: np.ndarray) -> str:
    h = img.shape[0]
    user_question = "附圖第一張為折線圖的下半部，第二張為同一個折線圖的上半部，請告訴我第一張圖中\"Y軸(即左邊縱向排列的數字)\"的最小值是多少，以及第二張圖中\"Y軸(即左邊縱向排列的數字)\"的最大值是多少，並將兩個數值以 python list 的形式表示。請只提供辨識出的數值，不要提供其他回答。"

    _, buffer = cv2.imencode('.png', img[0:int(h/2), :])
    # 把 numpy buffer 轉成 bytes
    img_bytes = buffer.tobytes()
    b64_image_up = types.Part.from_bytes(
        data=img_bytes,
        mime_type="image/png"
    )
    _, buffer = cv2.imencode('.png', img[int(h/2):h, :])
    # 把 numpy buffer 轉成 bytes
    img_bytes = buffer.tobytes()
    b64_image_down = types.Part.from_bytes(
        data=img_bytes,
        mime_type="image/png"
    )

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            user_question,
            b64_image_down,
            b64_image_up
        ])
    return response.text

def test_ai_y_value(image_data: bytes) -> Tuple[np.ndarray, list]:
    # 裁切出折線圖
    chart_images = get_line_graphs_by_title(image_data)

    y_vals = list()
    for i in range(len(chart_images)):
        # 把結果轉為陣列
        gemini_response = get_line_graph_y_value_ai_v2(chart_images[i])
        match = re.search(r"\[.*?\]", gemini_response)
        if match:
            list_str = match.group()
            result = ast.literal_eval(list_str)  # 轉成真正的 list
            y_vals.append(result)
        else:
            print("找不到 list")
    print(f"y_vals: {y_vals}")
    return chart_images, y_vals

# 建立轉換函數
def hour_to_pixel(x_val_start, x_val_end, x_pixel_start, x_pixel_end, x):
    return int(x_pixel_start + (x - x_val_start) * (x_pixel_end - x_pixel_start) / (x_val_end - x_val_start))

def pixel_to_kw(y_val_start, y_val_end, y_pixel_start, y_pixel_end, y):
    return y_val_start + (y_pixel_end - y) * (y_val_end - y_val_start) / (y_pixel_end - y_pixel_start)

# 抓座標對應值
def get_line_graph_values(chart_images: np.ndarray, line_graphs: np.ndarray, y_vals: list):
    i: int = 0
    if not line_graphs:
        print("no image received")
        return
    for graph in line_graphs:
        x_val_start = 1
        x_val_end = 24
        y_val_start = y_vals[i][0]
        y_val_end = y_vals[i][1]

        horizen_lines, draw_lines = get_filtered_lines(chart_images[i])
        sorted_horizen = sorted(horizen_lines)
        y_pixel_start = sorted_horizen[0]
        y_pixel_end = sorted_horizen[len(sorted_horizen) -1]
        # print(f'y_pixel_start: {y_pixel_start}\ny_pixel_end: {y_pixel_end}')

        # 找平均線輪廓
        contours, _ = cv2.findContours(graph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not contours:
            print(f"\nline graph {i+1} has no contours\n")
            i = i + 1
            continue
        # 抓面積最大的輪廓
        largest = max(contours, key=cv2.contourArea)
        
        # 取出折線的所有點座標 (轉成 list of (x, y))
        points = [tuple(pt[0]) for pt in largest]
        sorted_p = sorted(points, key=lambda p: p[0])
        x_pixel_start = sorted_p[0][0]
        x_pixel_end = sorted_p[len(sorted_p) - 1][0]
        # print(f'x_pixel_start: {x_pixel_start}\nx_pixel_end: {x_pixel_end}')

        # 建立一個每小時 (整數) 的對應值（可用最接近的點）
        hours = np.arange(1, 25)
        hour_to_kw = {}

        dev = (x_pixel_end - x_pixel_start) // 48

        for h in hours.tolist():
            x_target = hour_to_pixel(x_val_start, x_val_end, x_pixel_start, x_pixel_end, h)
            # 找出所有這個 x 附近的點（容許誤差 = dev）
            near_points = [p for p in points if abs(p[0] - x_target) <= dev]
            if near_points:
                y_avg = int(np.mean([p[1] for p in near_points]))
                hour_to_kw[h] = round(pixel_to_kw(y_val_start, y_val_end, y_pixel_start, y_pixel_end, y_avg))
        i = i + 1
        print(f"{i}:\n{hour_to_kw}")