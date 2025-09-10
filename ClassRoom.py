class ClassRoom:
    def __init__(self, building, floor, room_id, is_class_room):
        self.building = building  # 楼栋
        self.floor = floor  # 楼层
        self.room_id = room_id  # 号码
        self.is_class_room = is_class_room  # 是否为教室
        self.free_time = [
            {
                "section": section,
                "weeks": [
                    {"week": week, "weekDay": week_day, "isFree": True}
                    for week_day in range(1, 6)  # 周一到周五
                    for week in range(1, 19)  # 第1~18周
                ]
            }
            for section in ["0102", "0304", "0506", "0708", "0910"]
        ]

    def __repr__(self):
        return f"ClassRoom(building={self.building}, floor={self.floor}, room_id={self.room_id}, is_class_room={self.is_class_room})"