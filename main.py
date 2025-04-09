import re
import requests
import logging
from collections import OrderedDict
from datetime import datetime
import config
import time
import os

# 确保 output 文件夹存在
if not os.path.exists('output'):
    os.makedirs('output')

# 日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("function.log", "w", encoding="utf-8"), logging.StreamHandler()])

def parse_template(template_file):
    """
    解析模板文件，提取频道分类和频道名称。
    :param template_file: 模板文件路径
    :return: 包含频道分类和频道名称的有序字典
    """
    try:
        # 这里需要实现具体的解析逻辑
        pass
    except Exception as e:
        logging.error(f"Error parsing template file {template_file}: {e}")
        return OrderedDict()

def clean_channel_name(channel_name):
    """
    清洗频道名称，去除特殊字符并转换为大写。
    :param channel_name: 原始频道名称
    :return: 清洗后的频道名称
    """
    try:
        # 这里需要实现具体的清洗逻辑
        pass
    except Exception as e:
        logging.error(f"Error cleaning channel name {channel_name}: {e}")
        return channel_name

def fetch_channels(url):
    """
    从指定URL抓取频道列表。
    :param url: 直播源URL
    :return: 包含频道信息的有序字典
    """
    try:
        start_time = time.time()
        response = requests.get(url, timeout=10)
        response_time = time.time() - start_time
        if response.status_code == 200:
            if url.endswith('.m3u'):
                return parse_m3u_lines(response.text.splitlines(), response_time)
            elif url.endswith('.txt'):
                return parse_txt_lines(response.text.splitlines(), response_time)
    except requests.RequestException as e:
        logging.error(f"Failed to fetch channels from {url}: {e}")
    return OrderedDict()

def parse_m3u_lines(lines, response_time):
    """
    解析M3U格式的频道列表行。
    :param lines: M3U文件的行列表
    :param response_time: 响应时间
    :return: 包含频道信息的有序字典
    """
    channels = OrderedDict()
    current_category = None

    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF"):
            match = re.search(r'group-title="(.*?)" tvg-logo="(.*?)"?,(.*)', line)
            if match:
                current_category = match.group(1).strip()
                logo_url = match.group(2).strip() if match.group(2) else None
                channel_name = match.group(3).strip()
                if channel_name and channel_name.startswith("CCTV"):  # 判断频道名称是否存在且以CCTV开头
                    channel_name = clean_channel_name(channel_name)  # 频道名称数据清洗

                if current_category not in channels:
                    channels[current_category] = []
        elif line and not line.startswith("#"):
            channel_url = line.strip()
            if current_category and channel_name:
                # 添加频道信息到当前类别中，同时记录响应时间和logo_url
                channels[current_category].append((channel_name, channel_url, response_time, logo_url))

    return channels

def parse_txt_lines(lines, response_time):
    """
    解析TXT格式的频道列表行。
    :param lines: TXT文件的行列表
    :param response_time: 响应时间
    :return: 包含频道信息的有序字典
    """
    channels = OrderedDict()
    current_category = None

    for line in lines:
        line = line.strip()
        if "#genre#" in line:
            # 提取当前类别
            current_category = line.split(",")[0].strip()
            channels[current_category] = []
        elif current_category:
            match = re.match(r"^(.*?),(.*?)$", line)
            if match:
                channel_name = match.group(1).strip()
                if channel_name and channel_name.startswith("CCTV"):  # 判断频道名称是否存在且以CCTV开头
                    channel_name = clean_channel_name(channel_name)  # 频道名称数据清洗
                # 提取频道URL，并分割成多个部分
                channel_urls = match.group(2).strip().split('#')

                # 存储每个分割出的URL
                for channel_url in channel_urls:
                    channel_url = channel_url.strip()  # 去掉前后空白
                    # 这里假设txt格式没有logo信息，使用默认值
                    logo_url = None
                    channels[current_category].append((channel_name, channel_url, response_time, logo_url))
            elif line:
                # 这里假设txt格式没有logo信息，使用默认值
                logo_url = None
                channels[current_category].append((line, '', response_time, logo_url))

    return channels

def match_channels(template_channels, all_channels):
    """
    匹配模板中的频道与抓取到的频道。
    :param template_channels: 模板频道信息
    :param all_channels: 所有抓取到的频道信息
    :return: 匹配后的频道信息
    """
    try:
        # 这里需要实现具体的匹配逻辑
        pass
    except Exception as e:
        logging.error(f"Error matching channels: {e}")
        return OrderedDict()

def filter_source_urls(template_file):
    """
    过滤源URL，获取匹配后的频道信息。
    :param template_file: 模板文件路径
    :return: 匹配后的频道信息和模板频道信息
    """
    template_channels = parse_template(template_file)
    source_urls = config.source_urls

    all_channels = OrderedDict()
    for url in source_urls:
        fetched_channels = fetch_channels(url)
        merge_channels(all_channels, fetched_channels)

    matched_channels = match_channels(template_channels, all_channels)

    return matched_channels, template_channels

def merge_channels(target, source):
    """
    合并两个频道字典。
    :param target: 目标字典
    :param source: 源字典
    """
    for category, channels in source.items():
        if category not in target:
            target[category] = []
        target[category].extend(channels)

def is_ipv6(url):
    """
    判断URL是否为IPv6地址。
    :param url: 频道URL
    :return: 如果是IPv6地址返回True，否则返回False
    """
    try:
        # 这里需要实现具体的判断逻辑
        pass
    except Exception as e:
        logging.error(f"Error checking if URL {url} is IPv6: {e}")
        return False

def updateChannelUrlsM3U(channels, template_channels):
    """
    更新频道URL到M3U和TXT文件中。
    :param channels: 匹配后的频道信息
    :param template_channels: 模板频道信息
    """
    if channels is None:
        logging.error("Channels is None. Skipping update.")
        return
    written_urls = set()
    with open(os.path.join('output', 'live_ipv6.m3u'), 'w', encoding='utf-8') as f_m3u_ipv6, \
            open(os.path.join('output', 'live_ipv6.txt'), 'w', encoding='utf-8') as f_txt_ipv6, \
            open(os.path.join('output', 'live_ipv4.m3u'), 'w', encoding='utf-8') as f_m3u_ipv4, \
            open(os.path.join('output', 'live_ipv4.txt'), 'w', encoding='utf-8') as f_txt_ipv4:
        for category, channel_list in channels.items():
            f_m3u_ipv6.write(f"#EXTM3U group-title=\"{category}\"\n")
            f_txt_ipv6.write(f"{category},#genre#\n")
            f_m3u_ipv4.write(f"#EXTM3U group-title=\"{category}\"\n")
            f_txt_ipv4.write(f"{category},#genre#\n")
            channel_dict = OrderedDict()
            for channel_name, channel_url, response_time, logo_url in channel_list:
                if channel_name not in channel_dict:
                    channel_dict[channel_name] = []
                channel_dict[channel_name].append((channel_url, response_time, logo_url))

            for channel_name, urls in channel_dict.items():
                sorted_urls = sort_and_filter_urls(urls, written_urls)
                total_urls = len(sorted_urls)
                for index, (url, response_time, logo_url) in enumerate(sorted_urls, start=1):
                    if is_ipv6(url):
                        write_to_files(f_m3u_ipv6, f_txt_ipv6, category, channel_name, index, url, response_time, logo_url)
                    else:
                        write_to_files(f_m3u_ipv4, f_txt_ipv4, category, channel_name, index, url, response_time, logo_url)

def sort_and_filter_urls(urls, written_urls):
    """
    排序和过滤URL。
    :param urls: 频道URL列表
    :param written_urls: 已写入的URL集合
    :return: 排序和过滤后的URL列表
    """
    filtered_urls = [
        (url, response_time, logo_url) for url, response_time, logo_url in sorted(urls, key=lambda u: u[1])
        if url and url not in written_urls and not any(blacklist in url for blacklist in config.url_blacklist)
    ]
    written_urls.update([url for url, _, _ in filtered_urls])
    return filtered_urls

def add_url_suffix(url, index, total_urls, ip_version):
    """
    添加URL后缀。
    :param url: 原始URL
    :param index: 序号
    :param total_urls: 总URL数
    :param ip_version: IP版本
    :return: 添加后缀后的URL
    """
    try:
        # 这里需要实现具体的添加后缀逻辑
        pass
    except Exception as e:
        logging.error(f"Error adding URL suffix to {url}: {e}")
        return url

def write_to_files(f_m3u, f_txt, category, channel_name, index, new_url, response_time, logo_url):
    """
    写入M3U和TXT文件。
    :param f_m3u: M3U文件对象
    :param f_txt: TXT文件对象
    :param category: 频道分类
    :param channel_name: 频道名称
    :param index: 序号
    :param new_url: 新URL
    :param response_time: 响应时间
    :param logo_url: 图标URL
    """
    logo_url = logo_url if logo_url else ""
    f_m3u.write(f"#EXTINF:-1 group-title=\"{category}\" tvg-logo=\"{logo_url}\",{channel_name} - 线路{index}\n")
    f_m3u.write(f"{new_url}\n")
    f_txt.write(f"{channel_name},{new_url}\n")

if __name__ == "__main__":
    template_file = "demo.txt"
    channels, template_channels = filter_source_urls(template_file)
    updateChannelUrlsM3U(channels, template_channels)
