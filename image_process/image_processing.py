import cv2
import pytesseract
import re
import numpy as np
from typing import Tuple


# 提取文字(座標)
def extract_tick_values(thresh):
    # 設定參數提高中文辨識
    custom_config = r'--oem 3 --psm 4 -l chi_tra+eng'
    data = pytesseract.image_to_data(thresh, config=custom_config, output_type=pytesseract.Output.DICT)
    return data

# 定位著色圖座標
def find_color_table(image_data: bytes) -> Tuple[np.ndarray, tuple[int, int, int, int]]:
    img_nparry = np.fromstring(image_data, np.uint8)
    img = cv2.imdecode(img_nparry, cv2.IMREAD_COLOR)
    if img is None:
        print("圖片讀取失敗，請檢查路徑或檔案名稱")
        exit()        
    
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 二值化
    _, thresh = cv2.threshold(img_gray, 200, 255, cv2.THRESH_BINARY_INV)
    # 膨脹線條
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.dilate(thresh, kernel, iterations=2)
    # 找輪廓
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)   

    # 選擇最大面積的矩形
    max_area = 0
    target_rect = None
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        if area > max_area and w > 100 and h > 100:
            max_area = area
            target_rect = (x, y, w, h)
    return img, target_rect

def get_color_table_first_date(img_data):
    img_nparry = np.fromstring(img_data, np.uint8)
    img = cv2.imdecode(img_nparry, cv2.IMREAD_COLOR)
    if img is None:
        print("圖片讀取失敗，請檢查路徑或檔案名稱")
        exit()    
    
    h = img.shape[0]
    w = img.shape[1]
    y = round(h * 0.2)
    x = round(w * 0.12)

    date_text_area = img[0:y, 0:x]

    # 轉灰階 + 二值化
    gray = cv2.cvtColor(date_text_area, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

    data = extract_tick_values(thresh)

    for text in data['text']:
        match = re.search(r"\d+-\d+-\d+", text)
        if match:
            print("[test] first date of color table: ", text)
            return text

# 裁切著色圖
def get_color_table(image_data: bytes) -> np.ndarray:
    # 取得表格範圍
    img, target_rect = find_color_table(image_data)

    # 裁切表格
    if target_rect:
        x, y, w, h = target_rect
        table_area = img[y:y+h, x:x+w]
    
    return table_area

def get_mask_total(img_rgb: np.ndarray) -> np.ndarray:
    # 定義顏色範圍
    lower_null = np.array([240, 240, 240])
    upper_null = np.array([255, 255, 255])

    lower_blue = np.array([150, 200, 220])
    upper_blue = np.array([170, 210, 240])

    lower_red = np.array([230, 145, 150])
    upper_red = np.array([255, 165, 170])

    lower_orange = np.array([230, 170, 120])
    upper_orange = np.array([255, 200, 160])

    lower_yellow = np.array([230, 220, 30])
    upper_yellow = np.array([255, 255, 100])

    lower_green = np.array([120, 190, 120])
    upper_green = np.array([160, 225, 150])

    lower_purple = np.array([200, 160, 190])
    upper_purple = np.array([220, 170, 210])

    # 創建遮罩
    mask_null = cv2.inRange(img_rgb, lower_null, upper_null)
    mask_blue = cv2.inRange(img_rgb, lower_blue, upper_blue)
    mask_red = cv2.inRange(img_rgb, lower_red, upper_red)
    mask_orange = cv2.inRange(img_rgb, lower_orange, upper_orange)
    mask_yellow = cv2.inRange(img_rgb, lower_yellow, upper_yellow)
    mask_green = cv2.inRange(img_rgb, lower_green, upper_green)
    mask_purple = cv2.inRange(img_rgb, lower_purple, upper_purple)

    # 將遮罩合併
    mask_total = mask_null + mask_blue + mask_red + mask_orange + mask_yellow + mask_green + mask_purple
    mask_total = np.clip(mask_total, 0, 255)
    return mask_total

# 裁切折線圖(HSV)
def get_chart_by_hsv(image_data,
                      debug=False,
                      min_title_area=500,   # 篩選成為候選標題的最小面積 (視解析度調整)
                    ):
    img, table_cord = find_color_table(image_data)
    if table_cord:
        x, y, w, h = table_cord
        rightmost_x = x + w
        # 取得表格最右邊的 x 座標，根據該座標裁切圖檔
        graphs_area = img[:, rightmost_x:]
    
    hsv = cv2.cvtColor(graphs_area, cv2.COLOR_BGR2HSV)
    # 只保留黑色標題部分
    mask_color = cv2.inRange(hsv, (0, 0, 0), (179, 5, 50))  # H all, S < 5, V < 50
    debug_img = graphs_area.copy()  
    chart_masked = cv2.bitwise_and(debug_img, debug_img, mask=mask_color)
    masked_gray = cv2.cvtColor(chart_masked, cv2.COLOR_BGR2GRAY)
    _, title_thresh = cv2.threshold(masked_gray, 0, 255, cv2.THRESH_BINARY)

    thick_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (8, 3))
    thick_text_mask = cv2.morphologyEx(title_thresh, cv2.MORPH_DILATE, thick_kernel)
    # 做一次小膨脹，連接文字塊
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5,5))
    cleaned = cv2.dilate(thick_text_mask, kernel, iterations=1)

    # 找標題區塊輪廓
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    title_boxes = []
    for cnt in contours:
        x,y,ww,hh = cv2.boundingRect(cnt)
        area = ww*hh
        # 面積要夠大
        if area >= min_title_area:
            title_boxes.append((x,y,ww,hh,area))
    # 用 Y 排序
    title_sorted = sorted(title_boxes, key=lambda c: c[1])
    if debug:
        vis = graphs_area.copy()
        for (x,y,ww,hh,_) in title_boxes:
            cv2.rectangle(vis, (x,y), (x+ww,y+hh), (0,0,255), 2)

    return cut_line_chart(graphs_area, title_sorted)

def cut_line_chart(img, title_boxes, min_height=10):
    chart_images = []
    half_w = img.shape[1] // 2
    for i in range(len(title_boxes)):
        y_start = title_boxes[i][1]
        if i + 1 < len(title_boxes):  # 不是最後一張
            # 找 Y            
            if title_boxes[i+1][1] - title_boxes[i][1] > min_height:  # 下一張圖不在隔壁
                y_end = title_boxes[i+1][1]
            elif i + 2 < len(title_boxes):    # 下一張圖在隔壁而且正下方有圖
                y_end = title_boxes[i+2][1]
            else:       # 圖在最後一排
                y_end = img.shape[0]
            # 找 X
            if (i + 1) % 2 == 1:   # 圖在左
                x_start = 0
                x_end = half_w
            else:  # 圖在右
                x_start = half_w
                x_end = img.shape[1]
        else:
            y_end = img.shape[0]
            x_end = img.shape[1]
            if (i + 1) % 2 == 1:    # 最後一張，長條
                x_start = 0
            else:
                x_start = half_w
        if y_end - y_start > img.shape[0] // 2:
            y_end = y_start + (y_end - y_start) // 3
        print(f"[{i}][debug] y_start = {y_start}\n[{i}][debug] y_end = {y_end}")
        line_chart = img[y_start:y_end, x_start:x_end]
        chart_images.append(line_chart)
    return chart_images

# 補線
def gap_filling(masked_gray: np.ndarray):
    threshold = 1

    white_pixels = np.column_stack(np.where(masked_gray > 200))  # (y, x)
    sorted_pixels = white_pixels[np.argsort(white_pixels[:, 1])]

    x_diff = np.diff(sorted_pixels[:, 1])
    gap_indices_x = np.where(x_diff > threshold)[0]

    # X 方向
    for i in gap_indices_x:
        x1, y1 = sorted_pixels[i][1], sorted_pixels[i][0]
        x2, y2 = sorted_pixels[i+1][1], sorted_pixels[i+1][0]
        for x in range(x1+1, x2):
            alpha = (x - x1) / (x2 - x1)
            y = int(y1 + alpha * (y2 - y1))
            for dy in range(-2, 3):
                if 0 <= y + dy < masked_gray.shape[0]:
                        masked_gray[y + dy, x] = 255

        # Y 方向    
    for x in range(masked_gray.shape[1]):
        ys = white_pixels[white_pixels[:, 1] == x][:, 0]
        if len(ys) < 2:
            continue
        ys = np.sort(ys)
        y_diff = np.diff(ys)
        gap_indices_y = np.where((y_diff >= threshold) & (y_diff < 6))[0]
        for i in gap_indices_y:
            y1, y2 = ys[i], ys[i + 1]
            for y in range(y1 + 1, y2):
                masked_gray[y, x] = 255

# 處理折線圖
def line_graphs_processing(chart_images: np.ndarray) -> np.ndarray:
    line_graphs = list()
    if not chart_images:
        return None, None
    for chart in chart_images:
        s_threshold = adaptive_color_mask(chart)
        # 轉灰階 + 二值化
        gray = cv2.cvtColor(chart, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

        hsv = cv2.cvtColor(chart, cv2.COLOR_BGR2HSV)
        # 只保留彩色部分（排除灰階線）
        mask_color = cv2.inRange(hsv, (0, s_threshold, 80), (179, 255, 255))
        chart_masked = cv2.bitwise_and(chart, chart, mask=mask_color)
        masked_gray = cv2.cvtColor(chart_masked, cv2.COLOR_BGR2GRAY)
        
        # 開運算 + 腐蝕
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (4, 4))
        open_gray = cv2.morphologyEx(masked_gray, cv2.MORPH_OPEN, kernel)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        erosion_gray = cv2.morphologyEx(open_gray, cv2.MORPH_ERODE, kernel)

        x_min = 100
        x_max = erosion_gray.shape[1] - 50
        filtered_gray = erosion_gray.copy()
        filtered_gray[:, :x_min] = 0
        filtered_gray[:, x_max:] = 0

        # 補線
        gap_filling(filtered_gray)

        line_graphs.append(filtered_gray)
    return line_graphs

def adaptive_color_mask(img: np.ndarray):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    edges = cv2.Canny(v, 50, 150)
    edge_density = np.sum(edges > 0) / edges.size
    print("[debug] edge_density: ", edge_density)
    if edge_density < 0.06:
        s_threshold = 5
    else:
        s_threshold = 4

    return s_threshold

# 提取橫線
def get_filtered_lines(img: np.ndarray) -> Tuple[list, list]:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 邊緣偵測
    v = np.median(gray)
    print("[debug] v = ", v)
    edges = cv2.Canny(gray, int(0.03 * v), int(0.2 * v))

    projection = np.sum(edges, axis=1)  # 每一列的白點數
    threshold = np.max(projection) * 0.5
    line_y = np.where(projection > threshold)[0]

    # 去重複、合併相近的 y 值
    filtered_y = []
    for y in line_y:
        if not filtered_y or abs(y - filtered_y[-1]) > 5:
            filtered_y.append(y)

    # 找每條水平線的 X 範圍
    line_segments = []
    for y in filtered_y:
        row = edges[y, :]   # 該行的所有像素
        x_positions = np.where(row > 0)[0]  # 該行白點位置
        if len(x_positions) > 0:
            x1, x2 = x_positions.tolist()[0], x_positions.tolist()[-1]
            line_segments.append([x1, y.item(), x2, y.item()])
    # print(line_segments)
    lines = np.array(line_segments, dtype=np.int64).reshape(-1, 1, 4)
    
    draw_lines = []
    # 提取橫線 y 座標
    horizontal_lines = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if abs(y1 - y2) < 5 and abs(x2 - x1) > gray.shape[1] * 0.6:  # 判斷是否為橫線
            horizontal_lines.append(y1)
            draw_lines.append(line)

    # 排序並去除相近重複線
    horizontal_lines = sorted(horizontal_lines)
    filtered_lines = []
    threshold = 5  # 線距小於門檻視為同一條

    for y in horizontal_lines:
        if not filtered_lines or abs(y - filtered_lines[-1]) > threshold:
            filtered_lines.append(y)
    # print(len(filtered_lines))    
    return filtered_lines, draw_lines