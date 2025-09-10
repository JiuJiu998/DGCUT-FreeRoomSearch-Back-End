# 🎓 DGCUT-FreeRoomSearch-Back-End

基于 **Flask** 实现的后端服务，用于查询东莞理工学院城市学院的空闲教室。  
系统通过解析课表和教室数据，生成统一的 JSON 文件，供 API 接口查询。

---

## ✨ 功能特性

- ✅ 查询指定 **周次、星期、节次** 的空闲教室
- ✅ 支持连续节次空闲时间计算
- ✅ 支持按 **教学楼 / 楼层** 筛选教室
- ✅ 提供公告和使用说明接口
- ✅ 使用 JSON 文件作为数据源，方便更新和部署

---

## 🛠️ 技术栈

- **后端框架**: Flask
- **数据存储**: JSON 文件
- **配置文件**: config.ini

---

## 📂 项目结构

```plaintext
DGCUT-FreeRoomSearch-Back-End/
├── app.py                    # Flask 主程序
├── config.ini                # 配置文件（账号、文件路径）
├── total_schedule.json       # 总课表 + 教室闲置时间（最终数据文件）
├── requirements.txt          # Python 依赖
├── common.onnx...            # 图像转文本ddddocr库必需文件
└── ...
```

## ⚙️ 配置文件说明（config.ini）
在 config.ini 中设置账号和文件路径：

[account]\
userAccount=202200000000     # 教务系统账号\
password=password            # 教务系统密码

[fileName]
kbInfoSaveTo=kebiao.html                # 校园总课表 HTML\
roomFileXlsx=七号楼教室一览表.xlsx        # 教室情况 Excel\
roomInfoSaveTo=roomInfo.json            # 教室信息 JSON\
tableInfoSaveTo=tableInfo.json          # 总课表 JSON\
scheduleInfoSaveTo=total_schedule.json  # 教室闲置时间 JSON（Flask 使用的数据源）


## 🚀 安装与运行
1. 克隆仓库\
git clone git@github.com:JiuJiu998/DGCUT-FreeRoomSearch-Back-End.git\
cd DGCUT-FreeRoomSearch-Back-End
2. 安装依赖\
pip install -r requirements.txt\
3. 生成数据文件\
运行getSchedule.py，生成 total_schedule.json（即教室闲置时间表）。\
该文件路径需和 config.ini 中的 scheduleInfoSaveTo 保持一致。

4. 启动服务
python app.py\
默认运行在 http://0.0.0.0:5050。

## 🔗 API 接口
1. 查询空闲教室
GET /api/free_classrooms

### 参数：

week (int) 周次（1-18）

weekDay (int) 星期几（1-5，对应周一到周五）

section (str) 节次（0102, 0304, 0506, 0708, 0910）

building (可选) 教学楼编号

floor (可选) 楼层

### 示例：

curl "http://localhost:5050/api/free_classrooms?week=3&weekDay=2§ion=0304&building=七号楼"
返回：

json
{
  "success": true,
  "data": [
    {
      "building": "七号楼",
      "floor": "3",
      "room_id": "7301",
      "max_continuous": 3,
      "free_sections": ["0304", "0506", "0708"]
    }
  ],
  "msg": "找到 1 个教室，其从节次 0304 起有不同长度的连续空闲时间"
}
### 2. 公告
GET /api/announcement

返回公告内容。

### 3. 使用说明
GET /api/info

返回系统使用说明。

