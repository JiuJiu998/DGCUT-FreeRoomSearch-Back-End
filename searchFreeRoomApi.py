from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# 配置JSON文件路径（部署时可修改）
JSON_FILE_PATH = 'total_schedule.json'

# 定义节次顺序（用于连续节次查询）
SECTION_ORDER = ['0102', '0304', '0506', '0708', '0910']


def load_classroom_data():
    """加载教室数据"""
    try:
        if not os.path.exists(JSON_FILE_PATH):
            return None, f"JSON文件不存在: {JSON_FILE_PATH}"

        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f), None
    except Exception as e:
        return None, f"加载数据失败: {str(e)}"


def is_room_free_for_section(room, week, week_day, section):
    """检查指定节次是否空闲"""
    for time_slot in room['free_time']:
        if time_slot['section'] == section:
            for week_schedule in time_slot['weeks']:
                if (week_schedule['week'] == week and
                        week_schedule['weekDay'] == week_day):
                    return week_schedule['isFree']
    return False


def find_free_classrooms(data, week, week_day, section, building=None, floor=None):
    """从给定节次起，查找最大连续空闲节次的教室"""
    free_rooms = []

    try:
        start_index = SECTION_ORDER.index(section)
    except ValueError:
        return []

    for room in data:
        if not room.get('is_class_room', False):
            continue

        if building and room.get('building') != building:
            continue
        if floor and room.get('floor') != floor:
            continue

        max_free = 0
        free_sections = []

        for i in range(start_index, len(SECTION_ORDER)):
            current_section = SECTION_ORDER[i]
            if is_room_free_for_section(room, week, week_day, current_section):
                free_sections.append(current_section)
                max_free += 1
            else:
                break

        if max_free > 0:
            free_rooms.append({
                'building': room['building'],
                'floor': room['floor'],
                'room_id': room['room_id'],
                'max_continuous': max_free,
                'free_sections': free_sections
            })

    return free_rooms


@app.route('/api/free_classrooms', methods=['GET'])
def get_free_classrooms():
    week = request.args.get('week')
    week_day = request.args.get('weekDay')
    section = request.args.get('section')
    building = request.args.get('building')
    floor = request.args.get('floor')

    if not week or not week_day or not section:
        return jsonify({
            'success': False,
            'data': None,
            'msg': '缺少必要参数: week, weekDay, section'
        }), 400

    try:
        week = int(week)
        if week < 1 or week > 18:
            raise ValueError
    except ValueError:
        return jsonify({
            'success': False,
            'data': None,
            'msg': '周次必须是1-18之间的整数'
        }), 400

    if section not in SECTION_ORDER:
        return jsonify({
            'success': False,
            'data': None,
            'msg': f'节次参数无效，必须是以下之一: {", ".join(SECTION_ORDER)}'
        }), 400

    data, error = load_classroom_data()
    if error:
        return jsonify({
            'success': False,
            'data': None,
            'msg': error
        }), 500

    results = find_free_classrooms(data, week, week_day, section, building, floor)

    return jsonify({
        'success': True,
        'data': results,
        'msg': f'找到 {len(results)} 个教室，其从节次 {section} 起有不同长度的连续空闲时间'
    })


@app.route('/api/announcement', methods=['GET'])
def get_announcement():
    """获取公告内容"""
    announcement = {
        "title": "📢 公告",
        "lines": [
        ]
    }
    return jsonify({"success": True, "data": announcement})


@app.route('/api/info', methods=['GET'])
def get_info():
    """获取使用说明"""
    info = {
        "lines": [
        ]
    }
    return jsonify({"success": True, "data": info})


if __name__ == '__main__':
    # 部署时可修改host和port
    app.run(host='0.0.0.0', port=5050)
