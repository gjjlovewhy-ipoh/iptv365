import os
import requests
import yaml
from apscheduler.schedulers.background import BackgroundScheduler

# 读取配置
with open("config.yaml", "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

SOURCE_LIST = cfg["source_urls"]
OUT_PATH = cfg["out_file"]
UNIQUE = cfg["enable_unique"]
GROUP_RULE = cfg["group_rule"]

# 存储 {url:频道名}
channel_dict = {}

def get_group_by_name(name: str) -> str:
    """根据频道名称匹配分类"""
    name = name.upper()
    for group_name, keywords in GROUP_RULE.items():
        for kw in keywords:
            if kw.upper() in name:
                return group_name
    return "其他频道"

def fetch_one_source(url: str):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = requests.get(url, timeout=15, headers=headers)
        resp.encoding = resp.apparent_encoding
        text = resp.text.strip()
    except Exception as e:
        print(f"【抓取失败】{url} -> {str(e)}")
        return

    lines = text.splitlines()
    tmp_name = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            if "," in line:
                tmp_name = line.split(",")[-1].strip()
            continue
        if line.startswith("#"):
            continue
        # m3u播放地址
        if line.startswith("http"):
            ch_name = tmp_name if tmp_name else f"未知_{len(channel_dict)}"
            channel_dict[line] = ch_name
            tmp_name = ""
        # txt格式 名称,url
        elif "," in line and line.split(",")[-1].startswith("http"):
            ch_name, ch_url = line.rsplit(",", 1)
            channel_dict[ch_url.strip()] = ch_name.strip()

def build_m3u():
    channel_dict.clear()
    # 全线路抓取
    for src in SOURCE_LIST:
        fetch_one_source(src)

    # 组装m3u内容
    m3u = ["#EXTM3U"]
    for url, name in channel_dict.items():
        group = get_group_by_name(name)
        m3u.append(f'#EXTINF:-1 group-title="{group}",{name}')
        m3u.append(url)

    # 写入文件
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))
    print(f"✅ 生成完成，总频道：{len(channel_dict)}，文件：{OUT_PATH}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(build_m3u, "interval", hours=cfg["cron_hour"])
    scheduler.start()
    print("⏰ 定时任务启动：每1小时自动更新M3U")
    build_m3u()
    try:
        while True:
            input()
    except KeyboardInterrupt:
        scheduler.shutdown()

if __name__ == "__main__":
    start_scheduler()
