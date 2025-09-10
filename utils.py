import json
import os

import pandas as pd

from ClassRoom import ClassRoom


def read_class_room_data(excel_path):
    df = pd.read_excel(excel_path)

    # 确保列名和 Excel 表格一致
    required_columns = ['教学楼', '楼层', '教室号']
    if not all(col in df.columns for col in required_columns):
        raise ValueError(f"Excel 表头应包含: {required_columns}")

    class_rooms = []

    for _, row in df.iterrows():
        building = f"{row['教学楼']}"
        floor = row['楼层']
        room_id = row['教室号']

        is_class_room = (row['是否教室'] == "教室")

        room = ClassRoom(building, floor, room_id, is_class_room)
        class_rooms.append(room)

    return class_rooms


def convert_to_json(class_rooms):
    # 将 ClassRoom 对象列表转换为字典列表
    data = [room.__dict__ for room in class_rooms]

    # 转为 JSON 字符串，确保中文正常显示
    json_str = json.dumps(data, ensure_ascii=False, indent=4)
    return json_str


def save_json_to_file(json_data, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(json_data)


def load_json_from_file(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)
