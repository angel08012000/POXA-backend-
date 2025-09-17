import cv2, json, datetime, sys, os, re, ast
import numpy as np
import pathlib

from collections import defaultdict
from google import genai
from google.genai import types
from typing import Tuple

from image_process.image_processing import get_color_table, get_mask_total, get_line_graphs_by_title, get_filtered_lines

GEMINI_API_KEY = "AIzaSyAsO1xPnKc6YDfA3C01fEuG3-wF_7rEWEM"

def color_mapping(image_data: bytes, start_date_str: str) -> dict:
    img = get_color_table(image_data)
    # 轉換圖片從 BGR 到 RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    height, width, _ = img_rgb.shape

    color_ranges = {
        0: (np.array([240, 240, 240]), np.array([255, 255, 255])),  # null
        1: (np.array([150, 200, 220]), np.array([170, 210, 240])),  # blue
        2: (np.array([230, 140, 150]), np.array([255, 165, 170])),  # red
        3: (np.array([230, 170, 120]), np.array([255, 200, 160])),  # orange
        4: (np.array([230, 220, 30]), np.array([255, 255, 100])),  # yellow
        5: (np.array([120, 190, 120]), np.array([160, 225, 150])),   # green
        6: (np.array([200, 160, 190]), np.array([220, 170, 210]))   # purple
    }

    # 取得橫線
    filtered_lines, _ = get_filtered_lines(img, 'color')

    date_of_row = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
    # cell_height = height // rows
    rows = len(filtered_lines) - 1
    cols = 7
    cell_width = width // cols
    sample = 50
    result = dict()

    for r in range(rows):
        row_data = []
        for c in range(cols):
            # 取中間像素
            y1 = filtered_lines[r]
            y2 = filtered_lines[r+1]
            x = c * cell_width
            cell_img = img_rgb[y1:y2, x:x+cell_width]

            h, w = cell_img.shape[:2]
            code_dct = defaultdict(int)
            code = 9
            num_of_pixel = 0
            # 隨機取樣
            for _ in range(sample):
                x = np.random.randint(int(w*0.1), int(w*0.9))
                y = np.random.randint(int(h*0.1), int(h*0.9))
                pixel = cell_img[y, x]
                for k, (lower, upper) in color_ranges.items(): # 判斷是哪個顏色
                    if np.all(pixel >= lower) and np.all(pixel <= upper):
                        code_dct[k] = code_dct[k] + 1
                        num_of_pixel = num_of_pixel + 1
                        break
            # 計算各顏色的占比
            # print("[debug] num_of_pixel: ", num_of_pixel)
            if num_of_pixel > 0:
                for c in range(1, 7):
                    # print(f"{c}: {code_dct[c]}")
                    if code_dct[c] / num_of_pixel > 0.6:
                        code = c
            # print("="*10)
            # 若沒抓到顏色(code = 9)則用其他方法判斷(mask+bitwise_and)
            if code == 9:
                mask_total = get_mask_total(cell_img)
                cell_output = cv2.bitwise_and(cell_img, cell_img, mask=mask_total)
                
                nonzero_pixels = cell_output[np.any(cell_output != 0, axis=-1)] # 取出非零像素
                if len(nonzero_pixels) > 0:
                    avg_color = np.mean(nonzero_pixels, axis=0).astype(np.uint8)
                    for k, (lower, upper) in color_ranges.items():
                        if np.all(avg_color >= lower) and np.all(avg_color <= upper):
                            code = k
            row_data.append(code)
        
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

        horizen_lines, draw_lines = get_filtered_lines(chart_images[i], 'line')
        sorted_horizen = sorted(horizen_lines)
        y_pixel_start = sorted_horizen[0]
        y_pixel_end = sorted_horizen[-1]
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
        result.append(hour_to_kw)
    
    return result