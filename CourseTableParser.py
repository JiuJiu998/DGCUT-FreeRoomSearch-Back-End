import json
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Tuple

from utils import save_json_to_file


class CourseTableParser:
    def __init__(self, html_file: str, output_file: str):
        """
        初始化解析器
        :param html_file: 输入的课表 HTML 文件路径
        :param output_file: 输出 JSON 文件路径
        """
        self.html_file = html_file
        self.output_file = output_file

    @staticmethod
    def parse_weeks_and_location(lines: List[str]) -> List[Tuple[str, str]]:
        """
        从给定的行列表中解析出周次和地点的组合
        返回格式: [(周次1, 地点1), (周次2, 地点2), ...]
        """
        week_pattern = re.compile(r'\(([^)]*周)\)')
        separator_pattern = re.compile(r'-{5,}')

        results = []
        current_weeks = None
        current_location = None
        skip_next = False

        for i, line in enumerate(lines):
            if skip_next:
                skip_next = False
                continue

            if separator_pattern.match(line):
                if current_weeks and current_location:
                    for loc in current_location.split(','):
                        if loc.strip():
                            results.append((current_weeks, loc.strip()))
                current_weeks = None
                current_location = None
                continue

            week_match = week_pattern.search(line)
            if week_match:
                current_weeks = week_match.group(1)
                if i + 1 < len(lines) and not separator_pattern.match(lines[i + 1]):
                    next_line = lines[i + 1]
                    if not week_pattern.search(next_line) and not any(
                        char in next_line for char in ['(', ')', '教师', '班级']
                    ):
                        current_location = next_line
                        skip_next = True
                continue

            if not current_weeks and current_location is None:
                if (
                    not week_pattern.search(line)
                    and not any(char in line for char in ['(', ')', '教师', '班级'])
                    and not line.startswith(',')
                ):
                    current_location = line

        if current_weeks and current_location:
            for loc in current_location.split(','):
                if loc.strip():
                    results.append((current_weeks, loc.strip()))

        return results

    def parse_course_table_from_html2(self) -> List[Dict]:
        with open(self.html_file, "r", encoding="utf-8") as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table", id="timetable")
        if not table:
            raise ValueError("未找到 id='timetable' 的表格")

        rows = table.find_all("tr")[2:]

        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        sections = ["0102", "0304", "0506", "0708", "0910", "1112"]

        results = []

        for row in rows:
            cells = row.find_all("td")
            for index, cell in enumerate(cells[1:-1]):
                if cell.text.strip() == "":
                    continue
                weekday_index = index // 6
                section_index = index % 6

                divs = BeautifulSoup(cell.decode_contents(), "html.parser").find_all(
                    "div", class_="kbcontent1"
                )
                for div in divs:
                    text = div.get_text(separator="\n").strip()
                    lines = [line.strip() for line in text.splitlines() if line.strip()]

                    if len(lines) < 2:
                        continue

                    course_name = lines[0]
                    class_name = lines[1]

                    week_location_pairs = self.parse_weeks_and_location(lines[2:])
                    if not week_location_pairs:
                        week_location_pairs = self.parse_weeks_and_location(lines)

                    for weeks, location in week_location_pairs:
                        results.append({
                            "weekDay": weekdays[weekday_index],
                            "section": sections[section_index],
                            "courseName": course_name,
                            "className": class_name,
                            "weeks": weeks,
                            "classRoom": location
                        })

                    if not week_location_pairs:
                        results.append({
                            "weekDay": weekdays[weekday_index],
                            "section": sections[section_index],
                            "courseName": course_name,
                            "className": class_name,
                            "weeks": "未知周次",
                            "classRoom": "未知地点"
                        })

        return results

    @staticmethod
    def validate_parsing_results(results: List[Dict]) -> None:
        status_counts = {"success": 0, "missing_weeks": 0, "missing_location": 0}
        problems = []

        for record in results:
            week_issue = record["weeks"] in ["未知周次", ""]
            location_issue = record["classRoom"] in ["未知地点", ""]

            if week_issue and location_issue:
                status_counts["missing_weeks"] += 1
                status_counts["missing_location"] += 1
                problems.append(("both", record))
            elif week_issue:
                status_counts["missing_weeks"] += 1
                problems.append(("weeks", record))
            elif location_issue:
                status_counts["missing_location"] += 1
                problems.append(("location", record))
            else:
                status_counts["success"] += 1

        total = len(results)
        success_rate = (status_counts["success"] / total) * 100 if total > 0 else 0

        print("=" * 50)
        print("解析结果验证报告")
        print("=" * 50)
        print(f"总记录数: {total}")
        print(f"成功解析: {status_counts['success']} ({success_rate:.2f}%)")
        print(f"缺失周次: {status_counts['missing_weeks']}")
        print(f"缺失地点: {status_counts['missing_location']}")
        print("-" * 50)

        if problems:
            print("问题记录示例:")
            for issue_type, record in problems[:3]:
                print(f"类型: {issue_type}")
                print(f"解析结果: 周次={record['weeks']}, 地点={record['classRoom']}")
                print("-" * 50)

            with open("parsing_problems.json", "w", encoding="utf-8") as f:
                json.dump(problems, f, ensure_ascii=False, indent=2)
            print("完整问题记录已保存至: parsing_problems.json")
        else:
            print("所有记录解析成功!")

    @staticmethod
    def validate_with_patterns(results: List[Dict]):
        week_pattern = re.compile(r".*周$")
        location_pattern = re.compile(r".*[a-zA-Z0-9].{1,}")

        valid_count = 0
        invalid_records = []

        for record in results:
            weeks_valid = bool(week_pattern.match(record["weeks"])) if record["weeks"] else False
            location_valid = bool(location_pattern.match(record["classRoom"])) if record["classRoom"] else False

            if weeks_valid and location_valid:
                valid_count += 1
            else:
                invalid_records.append({
                    "record": record,
                    "weeks_valid": weeks_valid,
                    "location_valid": location_valid
                })

        print(f"格式验证结果: {valid_count}/{len(results)} 条记录符合格式要求")

        if invalid_records:
            print("问题记录示例:")
            for record_info in invalid_records[:3]:
                rec = record_info["record"]
                print(f"课程: {rec['courseName']}")
                print(f"周次: {rec['weeks']} ({'有效' if record_info['weeks_valid'] else '无效'})")
                print(f"地点: {rec['classRoom']} ({'有效' if record_info['location_valid'] else '无效'})")
                print("-" * 50)

    @staticmethod
    def check_data_consistency(results: List[Dict]):
        time_location_map = {}
        conflicts = []

        for record in results:
            key = (record["weekDay"], record["section"], record["classRoom"])
            if record["classRoom"] in ["未知地点", ""]:
                continue

            if key in time_location_map:
                existing_weeks = time_location_map[key]["weeks"]
                new_weeks = record["weeks"]

                if existing_weeks == new_weeks:
                    conflicts.append({
                        "location": key[2],
                        "time": f"{key[0]} {key[1]}节",
                        "existing": time_location_map[key],
                        "new": record
                    })
            else:
                time_location_map[key] = record

        if conflicts:
            print(f"发现 {len(conflicts)} 个潜在时间冲突:")
            for conflict in conflicts[:3]:
                print(f"冲突地点: {conflict['location']}")
                print(f"冲突时间: {conflict['time']}")
                print(f"现有课程: {conflict['existing']['courseName']} ({conflict['existing']['weeks']}周)")
                print(f"新课程: {conflict['new']['courseName']} ({conflict['new']['weeks']}周)")
                print("-" * 50)
        else:
            print("未发现时间地点冲突")

    def run(self):
        res = self.parse_course_table_from_html2()
        json_str = json.dumps(res, ensure_ascii=False, indent=2)
        save_json_to_file(json_str, self.output_file)

        return res
