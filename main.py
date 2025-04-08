import os
import re
import time
import requests
from collections import OrderedDict
import logging

# 配置日志记录
logging.basicConfig(filename='function.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

# 创建输出文件夹
output_folder = 'output'
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# 解析模板文件
def parse_template(template_file):
    template_channels = OrderedDict()
    current_category = None
    with open(template_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#EXTM3U'):
                continue
            if line.startswith('#EXTGRP:'):
                current_category = line[8:]
            elif line and not line.startswith('#'):
                if current_category not in template_channels:
                    template_channels[current_category] = []
                template_channels[current_category].append(line)
    return template_channels

# 清洗频道名称
def clean_channel_name(name):
    name = re.sub(r'[^\w\s]', '', name)
    return name.upper().strip()

# 抓取频道列表
def fetch_channels(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        lines = response.text.splitlines()
        channels = OrderedDict()
        current_category = None
        for line in lines:
            line = line.strip()
            if line.startswith('#EXTM3U'):
                continue
            if line.startswith('#EXTGRP:'):
                current_category = line[8:]
            elif line and not line.startswith('#'):
                if current_category not in channels:
                    channels[current_category] = []
                channels[current_category].append(line)
        return channels
    except requests.RequestException as e:
        logging.error(f"Error fetching channels from {url}: {e}")
        return OrderedDict()

# 解析 M3U 行
def parse_m3u_lines(lines):
    channels = OrderedDict()
    current_category = None
    current_info = None
    for line in lines:
        line = line.strip()
        if line.startswith('#EXTM3U'):
            continue
        if line.startswith('#EXTGRP:'):
            current_category = line[8:]
        elif line.startswith('#EXTINF:'):
            current_info = line
        elif line and not line.startswith('#'):
            if current_category not in channels:
                channels[current_category] = []
            channels[current_category].append((current_info, line))
    return channels

# 解析 TXT 行
def parse_txt_lines(lines):
    channels = OrderedDict()
    current_category = None
    for line in lines:
        line = line.strip()
        if line.startswith('#EXTGRP:'):
            current_category = line[8:]
        elif line and not line.startswith('#'):
            if current_category not in channels:
                channels[current_category] = []
            channels[current_category].append(line)
    return channels

# 测试响应时间
def test_response_time(url):
    try:
        start_time = time.time()
        response = requests.head(url, timeout=5)
        end_time = time.time()
        return end_time - start_time
    except requests.RequestException:
        return float('inf')

# 匹配频道
def match_channels(template_channels, fetched_channels):
    matched_channels = OrderedDict()
    for category, template_channel_names in template_channels.items():
        if category not in matched_channels:
            matched_channels[category] = []
        for template_name in template_channel_names:
            clean_template_name = clean_channel_name(template_name)
            best_match = None
            best_response_time = float('inf')
            for fetched_category, fetched_channel_info_list in fetched_channels.items():
                for fetched_info, fetched_url in fetched_channel_info_list:
                    fetched_name = re.search(r',(.*)$', fetched_info).group(1)
                    clean_fetched_name = clean_channel_name(fetched_name)
                    if clean_template_name == clean_fetched_name:
                        response_time = test_response_time(fetched_url)
                        if response_time < best_response_time:
                            best_match = (fetched_info, fetched_url)
                            best_response_time = response_time
            if best_match:
                matched_channels[category].append(best_match)
    return matched_channels

# 过滤源 URL
def filter_source_urls(template_file, source_urls):
    template_channels = parse_template(template_file)
    all_fetched_channels = OrderedDict()
    for url in source_urls:
        fetched_channels = fetch_channels(url)
        all_fetched_channels = merge_channels(all_fetched_channels, fetched_channels)
    matched_channels = match_channels(template_channels, all_fetched_channels)
    return matched_channels, template_channels

# 合并频道字典
def merge_channels(channel_dict1, channel_dict2):
    merged = channel_dict1.copy()
    for category, channels in channel_dict2.items():
        if category in merged:
            merged[category].extend(channels)
        else:
            merged[category] = channels
    return merged

# 判断是否为 IPv6 地址
def is_ipv6(url):
    try:
        parts = url.split('/')[2].split(':')
        if len(parts) > 2:
            return True
    except IndexError:
        pass
    return False

# 更新频道 URL 到 M3U 和 TXT 文件
def updateChannelUrlsM3U(template_file, source_urls):
    matched_channels, template_channels = filter_source_urls(template_file, source_urls)
    m3u_lines = ['#EXTM3U']
    txt_lines = []
    for category, channel_info_list in matched_channels.items():
        m3u_lines.append(f'#EXTGRP:{category}')
        txt_lines.append(f'#EXTGRP:{category}')
        for info, url in channel_info_list:
            m3u_lines.append(info)
            m3u_lines.append(url)
            txt_lines.append(url)
    m3u_file = os.path.join(output_folder, 'output.m3u')
    txt_file = os.path.join(output_folder, 'output.txt')
    write_to_files(m3u_lines, txt_lines, m3u_file, txt_file)

# 排序和过滤 URL
def sort_and_filter_urls(urls):
    filtered_urls = []
    for url in urls:
        if not is_ipv6(url):
            filtered_urls.append(url)
    return filtered_urls

# 添加 URL 后缀
def add_url_suffix(original_url, suffix):
    return original_url + suffix

# 写入文件
def write_to_files(m3u_lines, txt_lines, m3u_file, txt_file):
    with open(m3u_file, 'w', encoding='utf-8') as f:
        for line in m3u_lines:
            f.write(line + '\n')
    with open(txt_file, 'w', encoding='utf-8') as f:
        for line in txt_lines:
            f.write(line + '\n')

if __name__ == "__main__":
    template_file = 'demo.txt'
    source_urls = ['https://example.com/channels.m3u']  # 替换为实际的源 URL
    updateChannelUrlsM3U(template_file, source_urls)    
