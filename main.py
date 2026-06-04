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

channel_dict = {}

def get_group_by_name(name: str) -> str:
    name = name.upper()
    for group_name, keywords in GROUP_RULE.items():
        for kw in keywords:
            if kw.upper() in name:
                return group_name
    return "其他频道"

def fetch_one_source(url: str):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        resp = requests.get(url, timeout=10, headers=headers)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        text = resp.text.strip()
    except Exception as e:
        print(f"【跳过失效源】{url} | 错误:{str(e)}")
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
        if line.startswith("http"):
            ch_name = tmp_name if tmp_name else f"未知_{len(channel_dict)}"
            channel_dict[line] = ch_name
            tmp_name = ""
        elif "," in line and line.rsplit(",",1)[-1].startswith("http"):
            try:
                ch_name, ch_url = line.rsplit(",", 1)
                channel_dict[ch_url.strip()] = ch_name.strip()
            except:
                continue

def build_m3u():
    channel_dict.clear()
    for src in SOURCE_LIST:
        fetch_one_source(src)

    m3u = ["#EXTM3U"]
    for url, name in channel_dict.items():
        group = get_group_by_name(name)
        m3u.append(f'#EXTINF:-1 group-title="{group}",{name}')
        m3u.append(url)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))
    print(f"✅ 生成完成，总频道：{len(channel_dict)}")

# Action云端只执行一次生成，不启用后台定时阻塞
if __name__ == "__main__":
    import sys
    # 判断环境：Github Action直接生成退出，本地运行开启定时
    if "CI" in os.environ:
        build_m3u()
    else:
        scheduler = BackgroundScheduler()
        scheduler.add_job(build_m3u, "interval", hours=cfg["cron_hour"])
        scheduler.start()
        build_m3u()
        print("⏰本地定时启动，每小时更新")
        try:
            while True:
                input()
        except KeyboardInterrupt:
            scheduler.shutdown()
