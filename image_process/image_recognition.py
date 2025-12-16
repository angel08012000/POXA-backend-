import cv2, json, datetime, sys, os, re, ast
import numpy as np
import pathlib

from collections import defaultdict
from google import genai
from google.genai import types
from typing import Tuple

from image_process.image_processing import get_color_table, get_mask_total, get_chart_by_hsv, get_filtered_lines

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

def color_mapping(image_data: bytes, start_date_str: str) -> dict:
    img, circle_colors = get_color_table(image_data)
    # 轉換圖片從 BGR 到 RGB
    img_rgb = img.copy()
    height, width, _ = img_rgb.shape

    # 取得橫線
    horizontal_filtered_lines, vertical_filtered_lines, _ = get_filtered_lines(img)

    date_of_row = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
    # cell_height = height // rows
    rows = len(horizontal_filtered_lines) - 1
    cols = 7
    cell_width = width // cols
    sample = 50
    result = dict()

    for r in range(rows):
        row_data = []
        y1 = horizontal_filtered_lines[r]
        y2 = horizontal_filtered_lines[r+1]
        # print(date_of_row)
        for col in range(cols):
            x1 = vertical_filtered_lines[col]
            x2 = vertical_filtered_lines[col+1]
            cell_img = img_rgb[y1:y2, x1:x2]

            h, w = cell_img.shape[:2]
            code_dct = defaultdict(int)
            code = 9
            min_dist = float('inf')
            avg_color = np.mean(cell_img, axis=0).astype(np.uint8)
            for k, circle_rgb in circle_colors.items():
                dist = np.linalg.norm(avg_color - np.array(circle_rgb))
                if dist < min_dist:
                    min_dist = dist
                    code = k
            row_data.append(code)
        
        # print(row_data)
        result[date_of_row.strftime('%Y-%m-%d')] = row_data
        date_of_row = date_of_row + datetime.timedelta(days=7)
    
    return result

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

    client = genai.Client(api_key=config.GEMINI_API_KEY)
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
    chart_images = get_chart_by_hsv(image_data)
    if not chart_images:
        print("[error] no images cutted")
        return None, None

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
    result = list()
    if not line_graphs:
        print("no image received")
        return
    for graph in line_graphs:
        x_val_start = 1
        x_val_end = 24
        y_val_start = y_vals[i][0]
        y_val_end = y_vals[i][1]

        horizen_lines, _, draw_lines = get_filtered_lines(chart_images[i])
        sorted_horizen = sorted(horizen_lines)
        y_pixel_start = sorted_horizen[0]
        y_pixel_end = sorted_horizen[-1]

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
        result.append(hour_to_kw)
    
    return result