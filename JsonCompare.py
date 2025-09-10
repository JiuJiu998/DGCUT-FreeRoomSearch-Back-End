import json

with open("roomBase_with_schedule 2025-09-10 -2.json", "r", encoding="utf-8") as f1, open("roomBase_with_schedule 2025-09-10.json", "r", encoding="utf-8") as f2:
    data1 = json.load(f1)
    data2 = json.load(f2)

if data1 == data2:
    print("✅ 两个 JSON 完全一致！")
else:
    print("❌ JSON 不一致！")
