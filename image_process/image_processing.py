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

# 裁切折線圖(用標題去裁)
def get_line_graphs_by_title(image_data: bytes) -> np.ndarray:
    img, table_cord = find_color_table(image_data)
    if table_cord:
        x, y, w, h = table_cord
        rightmost_x = x + w

        # 取得表格最右邊的 x 座標，根據該座標裁切圖檔
        graphs_area = img[:, rightmost_x:]

        # 轉灰階 + 二值化
        gray = cv2.cvtColor(graphs_area, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

        # 提取文字(座標)
        data = extract_tick_values(thresh)

        # 找出文字區塊
        title_boxes_y = []
        for i, text in enumerate(data['text']):
            if '類' in text:
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                title_boxes_y.append((x, y, w, h))

        # 擷取折線圖
        chart_images = []
        print(f"[debug] num of chart y: {len(title_boxes_y)}")
        if len(title_boxes_y) == 0:
            return None

        for i in range(len(title_boxes_y)):
            y_start = title_boxes_y[i][1]   # 最上面的 y
            if i + 1 < len(title_boxes_y):  # 不是最後一張
                # 找 y
                if title_boxes_y[i+1][1] - title_boxes_y[i][1] > 100:   # 下一張圖不是在隔壁
                    y_end = title_boxes_y[i + 1][1]
                elif i + 2 < len(title_boxes_y):    # 下一張圖在隔壁而且正下方有圖
                    y_end = title_boxes_y[i + 2][1]
                else:   # 圖在最後一排
                    y_end = img.shape[0]
                # 找 x
                if (i + 1) % 2 == 1:    # 圖在左側
                    x_start = 0
                    x_end = graphs_area.shape[1] // 2
                else:   # 圖在右側
                    x_start = graphs_area.shape[1] // 2
                    x_end = graphs_area.shape[1]
            else:
                y_end = img.shape[0]
                if (i + 1) % 2 == 1:    # 最後一張，長條
                    x_start = 0
                    x_end = graphs_area.shape[1]
                else:   # 最後一張，方形
                    x_start = graphs_area.shape[1] // 2
                    x_end = graphs_area.shape[1]

            chart = graphs_area[y_start:y_end, x_start:x_end]
            chart_images.append(chart)
        return chart_images

# 補線
def gap_filling(masked_gray: np.ndarray):
    threshold = 2

    white_pixels = np.column_stack(np.where(masked_gray > 200))  # (y, x)
    sorted_pixels = white_pixels[np.argsort(white_pixels[:, 1])]

    x_diff = np.diff(sorted_pixels[:, 1])
    gap_indices = np.where(x_diff > threshold)[0]

    for i in gap_indices:
        x1, y1 = sorted_pixels[i][1], sorted_pixels[i][0]
        x2, y2 = sorted_pixels[i+1][1], sorted_pixels[i+1][0]
        for x in range(x1+1, x2):
            alpha = (x - x1) / (x2 - x1)
            y = int(y1 + alpha * (y2 - y1))
            masked_gray[y, x] = 255
            masked_gray[y+1, x] = 255
            masked_gray[y-1, x] = 255

# 處理折線圖
def line_graphs_processing(chart_images: np.ndarray) -> np.ndarray:
    line_graphs = list()
    if not chart_images:
        return None, None
    for chart in chart_images:
        # 轉灰階 + 二值化
        gray = cv2.cvtColor(chart, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

        hsv = cv2.cvtColor(chart, cv2.COLOR_BGR2HSV)
        # 只保留彩色部分（排除灰階線）
        mask_color = cv2.inRange(hsv, (0, 10, 80), (180, 255, 255))  # S > 10，V > 80
        chart_masked = cv2.bitwise_and(chart, chart, mask=mask_color)
        masked_gray = cv2.cvtColor(chart_masked, cv2.COLOR_BGR2GRAY)
        
        x_min = 100
        x_max = masked_gray.shape[1] - 50
        filtered_gray = masked_gray.copy()
        filtered_gray[:, :x_min] = 0
        filtered_gray[:, x_max:] = 0

        # 補線
        gap_filling(filtered_gray)

        line_graphs.append(filtered_gray)
    return line_graphs

# 提取橫線
def get_filtered_lines(img: np.ndarray, method: str) -> Tuple[list, list]:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if method == 'color':
        # 邊緣偵測
        v = np.median(gray)
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
        lines = np.array(line_segments, dtype=np.int64).reshape(-1, 1, 4)

    elif method == 'line':
        gray = cv2.GaussianBlur(gray, (3,3), 0)   # 平滑雜訊
        gray = cv2.equalizeHist(gray)             # 均衡化，拉高線條對比
        # 邊緣偵測
        edges = cv2.Canny(gray, 10, 80, apertureSize=3)
        # 偵測橫向線段
        minLine = img.shape[1] * 0.6
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=10, minLineLength=minLine, maxLineGap=10)
    
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