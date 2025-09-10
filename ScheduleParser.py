import json
import re
from collections import defaultdict
import openpyxl

# 星期映射表
WEEKDAY_MAPPING = {
    "星期一": 1,
    "星期二": 2,
    "星期三": 3,
    "星期四": 4,
    "星期五": 5
}

# 反转映射用于查找
REVERSE_WEEKDAY_MAPPING = {v: k for k, v in WEEKDAY_MAPPING.items()}


class ClassScheduleProcessor:
    def __init__(self, room_base_file, schedule_file, output_file, debug_excel="process_log.xlsx"):
        # 文件路径
        self.room_base_file = room_base_file
        self.schedule_file = schedule_file
        self.output_file = output_file
        self.debug_excel = debug_excel

        # 计数器
        self.normalize_failed_counter = 0
        self.room_not_found_counter = 0
        self.weeks_parse_failed_counter = 0
        self.success_counter = 0
        self.failed_examples = []

        # 教室字典 { (building, room_id): ClassRoom }
        self.classrooms = {}

    # ------------------ 工具方法 ------------------
    def parse_weeks(self, weeks_str):
        """解析周次字符串，返回周次列表"""
        cleaned = re.sub(r'[()周]', '', weeks_str)
        cleaned = cleaned.replace("单周", "").replace("双周", "")
        periods = re.split(r'[,，]', cleaned)

        week_list = []
        for period in periods:
            period = period.strip()
            if not period:
                continue
            if '-' in period:
                try:
                    start, end = map(int, period.split('-'))
                    week_list.extend(range(start, end + 1))
                except:
                    self.weeks_parse_failed_counter += 1
                    continue
            elif period.isdigit():
                week_list.append(int(period))
            elif '单' in period or '双' in period:
                try:
                    week_num = int(re.sub(r'[单双]', '', period))
                    week_list.append(week_num)
                except:
                    self.weeks_parse_failed_counter += 1
                    continue
            else:
                self.weeks_parse_failed_counter += 1
                continue
        return sorted(set(week_list))

    def normalize_classroom(self, classroom_str):
        """标准化教室名称"""
        if "校内" in classroom_str or "实验" in classroom_str or "琴房" in classroom_str:
            self.normalize_failed_counter += 1
            return None

        patterns = [
            r'(\d+)号楼([A-Za-z])(\d+)',
            r'(\d+)号楼([A-Za-z])区(\d+)',
            r'(\d+)([A-Za-z])?(\d+)',
            r'([A-Za-z]?\d+[A-Za-z]?\d+)',
            r'(\d+)([A-Za-z])(\d+)',
            r'([A-Za-z]?\d+)楼?([A-Za-z]?)(\d+)',
        ]

        for pattern in patterns:
            match = re.match(pattern, classroom_str)
            if match:
                groups = match.groups()
                building_num = groups[0]
                zone = groups[1] if len(groups) > 1 and groups[1] else ""
                room_id = groups[2] if len(groups) > 2 else groups[1] if len(groups) > 1 else ""

                if zone:
                    building = f"{building_num}号楼{zone.upper()}区"
                else:
                    building = f"{building_num}号楼"

                if room_id:
                    floor_num = room_id[0]
                    floor_mapping = {
                        "1": "一楼", "2": "二楼", "3": "三楼", "4": "四楼",
                        "5": "五楼", "6": "六楼", "7": "七楼", "8": "八楼",
                        "9": "九楼", "0": "一楼"
                    }
                    floor = floor_mapping.get(floor_num, f"{floor_num}楼")
                else:
                    floor = "一楼"

                return {
                    "building": building,
                    "floor": floor,
                    "room_id": int(room_id) if room_id and room_id.isdigit() else 0
                }

        self.normalize_failed_counter += 1
        return None

    # ------------------ ClassRoom 内部类 ------------------
    class ClassRoom:
        def __init__(self, building, floor, room_id, is_class_room):
            self.building = building
            self.floor = floor
            self.room_id = room_id
            self.is_class_room = is_class_room
            self.schedule = {}
            for section in ["0102", "0304", "0506", "0708", "0910"]:
                self.schedule[section] = {}
                for week in range(1, 19):
                    self.schedule[section][week] = {
                        1: True, 2: True, 3: True, 4: True, 5: True
                    }

        def mark_occupied(self, week_day, section, weeks):
            week_day_num = WEEKDAY_MAPPING.get(week_day)
            if not week_day_num:
                return
            for week in weeks:
                if 1 <= week <= 18:
                    if section in self.schedule and week in self.schedule[section]:
                        if week_day_num in self.schedule[section][week]:
                            self.schedule[section][week][week_day_num] = False

        def to_free_time(self):
            free_time = []
            for section, week_data in self.schedule.items():
                weeks_list = []
                for week, day_data in week_data.items():
                    for day_num, is_free in day_data.items():
                        weeks_list.append({
                            "week": week,
                            "weekDay": REVERSE_WEEKDAY_MAPPING[day_num],
                            "isFree": is_free
                        })
                weeks_list.sort(key=lambda x: (x["week"], WEEKDAY_MAPPING[x["weekDay"]]))
                free_time.append({"section": section, "weeks": weeks_list})
            return free_time

        def to_dict(self):
            return {
                "building": self.building,
                "floor": self.floor,
                "room_id": self.room_id,
                "is_class_room": self.is_class_room,
                "free_time": self.to_free_time()
            }

    # ------------------ 主处理流程 ------------------
    def load_classrooms(self):
        """加载roomBase.json"""
        try:
            with open(self.room_base_file, "r", encoding="utf-8") as f:
                room_data = json.load(f)

            for room in room_data:
                room_id = int(room["room_id"]) if isinstance(room["room_id"], str) and room["room_id"].isdigit() else room["room_id"]
                key = (room["building"], room_id)
                self.classrooms[key] = self.ClassRoom(
                    room["building"], room["floor"], room_id, room["is_class_room"]
                )

            print(f"成功加载 {len(self.classrooms)} 个教室")
        except Exception as e:
            print(f"加载教室数据失败: {str(e)}")

    def process_schedule(self):
        """处理课表数据，更新教室占用状态，并写Excel日志"""
        try:
            with open(self.schedule_file, "r", encoding="utf-8") as f:
                schedule_data = json.load(f)

            total_records = len(schedule_data)
            print(f"开始处理 {total_records} 条课表记录")

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "处理日志"
            ws.append(["序号", "weekDay", "section", "courseName", "className", "weeks", "classRoom",
                       "标准化结果", "教室键", "解析周次", "处理结果"])

            for i, entry in enumerate(schedule_data):
                result_msg, room_info_str, room_key_str, weeks_list_str = "", "", "", ""

                if "classRoom" not in entry or "weeks" not in entry or "weekDay" not in entry or "section" not in entry:
                    result_msg = "❌ 缺少必要字段"
                    self.failed_examples.append({"reason": "缺少必要字段", "entry": entry})
                else:
                    room_info = self.normalize_classroom(entry["classRoom"])
                    room_info_str = str(room_info)
                    if not room_info:
                        result_msg = "❌ 教室标准化失败"
                        self.failed_examples.append({"reason": "教室标准化失败", "entry": entry})
                    else:
                        room_key = (room_info["building"], room_info["room_id"])
                        room_key_str = str(room_key)
                        if room_key not in self.classrooms:
                            result_msg = "❌ 教室未找到"
                            self.failed_examples.append({"reason": "教室未找到", "room_key": room_key, "entry": entry})
                            self.room_not_found_counter += 1
                        else:
                            weeks_list = self.parse_weeks(entry["weeks"])
                            weeks_list_str = str(weeks_list)
                            if not weeks_list:
                                result_msg = "❌ 周次解析为空"
                                self.failed_examples.append({"reason": "周次解析为空", "weeks": entry["weeks"], "entry": entry})
                            else:
                                self.classrooms[room_key].mark_occupied(entry["weekDay"], entry["section"], weeks_list)
                                self.success_counter += 1
                                result_msg = "✅ 已标记占用"

                ws.append([
                    i+1, entry.get("weekDay", ""), entry.get("section", ""), entry.get("courseName", ""),
                    entry.get("className", ""), entry.get("weeks", ""), entry.get("classRoom", ""),
                    room_info_str, room_key_str, weeks_list_str, result_msg
                ])

            wb.save(self.debug_excel)
            print(f"处理日志已保存到 {self.debug_excel}")

        except Exception as e:
            print(f"处理课表数据时出错: {str(e)}")
            import traceback
            traceback.print_exc()

    def save_results(self):
        """保存最终结果"""
        try:
            result = [room.to_dict() for room in self.classrooms.values()]
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"结果已保存到 {self.output_file}")
        except Exception as e:
            print(f"保存结果失败: {str(e)}")

    def run(self):
        """执行完整流程"""
        print("=" * 50)
        print("教室空闲时间计算器")
        print("=" * 50)

        self.load_classrooms()
        if not self.classrooms:
            print("错误: 未加载任何教室数据，程序终止")
            return

        self.process_schedule()
        self.save_results()

        print("\n处理结果统计:")
        print(f"成功标记的占用次数: {self.success_counter}")
        print(f"教室标准化失败次数: {self.normalize_failed_counter}")
        print(f"教室未找到次数: {self.room_not_found_counter}")
        print(f"周次解析失败次数: {self.weeks_parse_failed_counter}")

        if self.failed_examples:
            print(f"\n失败记录总数: {len(self.failed_examples)}")
            for i, example in enumerate(self.failed_examples[:5]):
                print(f"示例 {i+1}: {example['reason']}")
                print(f"  完整记录: {json.dumps(example.get('entry', {}), ensure_ascii=False, indent=2)}")
                print("-" * 50)

        total_slots = 0
        occupied_slots = 0
        for room in self.classrooms.values():
            for section in room.schedule.values():
                for week_data in section.values():
                    for is_free in week_data.values():
                        total_slots += 1
                        if not is_free:
                            occupied_slots += 1

        print("\n最终统计:")
        print(f"总时间槽位: {total_slots}")
        print(f"占用槽位: {occupied_slots} ({occupied_slots / total_slots:.2%})")
        print(f"空闲槽位: {total_slots - occupied_slots} ({(total_slots - occupied_slots) / total_slots:.2%})")


# ------------------ 使用示例 ------------------
# if __name__ == "__main__":
#     processor = ClassScheduleProcessor(
#         room_base_file="roomInfo.json",
#         schedule_file="tableInfo.json",
#         output_file="roomBase_with_schedule 2025-09-10.json",
#         debug_excel="process_log.xlsx"
#     )
#     processor.run()
