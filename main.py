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
    :return: 包含频道分类、频道名称和 logo URL 的有序字典
    """
    template_channels = OrderedDict()
    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    parts = line.strip().split(',')
                    if len(parts) >= 3:
                        category, channel_name, logo_url = parts[:3]
                        template_channels[channel_name] = {
                            'category': category,
                            'logo_url': logo_url
                        }
    except Exception as e:
        logging.error(f"Error parsing template file: {e}")
    return template_channels

def clean_channel_name(channel_name):
    """
    清洗频道名称，去除特殊字符并转换为大写。
    :param channel_name: 原始频道名称
    :return: 清洗后的频道名称
    """
    cleaned_name = re.sub(r'[^\w\s]', '', channel_name).strip().upper()
    return cleaned_name

def fetch_channels(url):
    """
    从指定URL抓取频道列表。
    :param url: 直播源URL
    :return: 包含频道信息（名称、URL、logo URL、响应时间）的有序字典
    """
    all_channels = OrderedDict()
    try:
        response = requests.get(url)
        if response.status_code == 200:
            lines = response.text.splitlines()
            if url.endswith('.m3u'):
                all_channels = parse_m3u_lines(lines)
            elif url.endswith('.txt'):
                all_channels = parse_txt_lines(lines)
    except Exception as e:
        logging.error(f"Error fetching channels from {url}: {e}")
    return all_channels

def parse_m3u_lines(lines):
    """
    解析M3U格式的频道列表行。
    :param lines: M3U文件的行列表
    :return: 包含频道信息（名称、URL、logo URL、响应时间）的有序字典
    """
    channels = OrderedDict()
    current_channel = None
    for line in lines:
        if line.startswith('#EXTINF:'):
            parts = line.split(',', 1)
            if len(parts) == 2:
                info = parts[0]
                channel_name = parts[1]
                logo_match = re.search(r'tvg-logo="([^"]+)"', info)
                logo_url = logo_match.group(1) if logo_match else ''
                current_channel = {
                    'name': channel_name,
                    'logo_url': logo_url
                }
        elif line.startswith('http') and current_channel:
            current_channel['url'] = line
            try:
                start_time = time.time()
                test_response = requests.get(line, timeout=5)
                response_time = time.time() - start_time
                current_channel['response_time'] = response_time
            except Exception as e:
                current_channel['response_time'] = float('inf')
            channels[current_channel['name']] = current_channel
            current_channel = None
    return channels

def parse_txt_lines(lines):
    """
    解析TXT格式的频道列表行。
    :param lines: TXT文件的行列表
    :return: 包含频道信息（名称、URL、logo URL、响应时间）的有序字典
    """
    channels = OrderedDict()
    for line in lines:
        if line.strip():
            parts = line.strip().split(',')
            if len(parts) >= 3:
                channel_name, url, logo_url = parts[:3]
                try:
                    start_time = time.time()
                    test_response = requests.get(url, timeout=5)
                    response_time = time.time() - start_time
                except Exception as e:
                    response_time = float('inf')
                channels[channel_name] = {
                    'name': channel_name,
                    'url': url,
                    'logo_url': logo_url,
                    'response_time': response_time
                }
    return channels

def match_channels(template_channels, all_channels):
    """
    匹配模板中的频道与抓取到的频道，选择响应时间最短的。
    :param template_channels: 模板频道信息
    :param all_channels: 所有抓取到的频道信息
    :return: 匹配后的频道信息
    """
    matched_channels = OrderedDict()
    for channel_name, template_info in template_channels.items():
        cleaned_template_name = clean_channel_name(channel_name)
        best_match = None
        best_response_time = float('inf')
        for fetched_name, fetched_info in all_channels.items():
            cleaned_fetched_name = clean_channel_name(fetched_name)
            if cleaned_template_name == cleaned_fetched_name:
                if fetched_info['response_time'] < best_response_time:
                    best_match = fetched_info
                    best_response_time = fetched_info['response_time']
        if best_match:
            matched_channels[channel_name] = {
                'category': template_info['category'],
                'url': best_match['url'],
                'logo_url': best_match.get('logo_url', template_info['logo_url']),
                'response_time': best_match['response_time']
            }
    return matched_channels

def filter_source_urls(template_file):
    """
    过滤源URL，获取匹配后的频道信息。
    :param template_file: 模板文件路径
    :return: 匹配后的频道信息和模板频道信息
    """
    template_channels = parse_template(template_file)
    all_channels = OrderedDict()
    for url in config.SOURCE_URLS:
        fetched_channels = fetch_channels(url)
        merge_channels(all_channels, fetched_channels)
    channels = match_channels(template_channels, all_channels)
    return channels, template_channels

def merge_channels(target, source):
    """
    合并两个频道字典。
    :param target: 目标字典
    :param source: 源字典
    """
    for channel_name, channel_info in source.items():
        if channel_name not in target:
            target[channel_name] = channel_info

def is_ipv6(url):
    """
    判断URL是否为IPv6地址。
    :param url: 频道URL
    :return: 如果是IPv6地址返回True，否则返回False
    """
    pattern = re.compile(r'^\[?[0-9a-fA-F:]+]?(:\d+)?$')
    return bool(pattern.match(url))

def updateChannelUrlsM3U(channels, template_channels):
    """
    更新频道URL到M3U和TXT文件中。
    :param channels: 匹配后的频道信息
    :param template_channels: 模板频道信息
    """
    try:
        with open('output/output.m3u', 'w', encoding='utf-8') as f_m3u, \
                open('output/output.txt', 'w', encoding='utf-8') as f_txt:
            f_m3u.write('#EXTM3U\n')
            index = 1
            for channel_name, channel_info in channels.items():
                category = channel_info['category']
                new_url = channel_info['url']
                response_time = channel_info['response_time']
                logo_url = channel_info['logo_url']
                write_to_files(f_m3u, f_txt, category, channel_name, index, new_url, response_time, logo_url)
                index += 1
    except Exception as e:
        logging.error(f"Error updating channel URLs: {e}")

def sort_and_filter_urls(urls, written_urls):
    """
    排序和过滤URL。
    :param urls: 频道URL列表
    :param written_urls: 已写入的URL集合
    :return: 排序和过滤后的URL列表
    """
    sorted_urls = sorted(urls, key=lambda x: (is_ipv6(x), x))
    filtered_urls = [url for url in sorted_urls if url not in written_urls]
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
    suffix = f"?index={index}&total={total_urls}&ip_version={ip_version}"
    return url + suffix

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
    f_m3u.write(f'#EXTINF:-1 group-title="{category}" tvg-logo="{logo_url}",{channel_name} (Response Time: {response_time:.3f}s)\n')
    f_m3u.write(f'{new_url}\n')
    f_txt.write(f'{channel_name},{new_url},{logo_url},{response_time:.3f}\n')

if __name__ == "__main__":
    template_file = "demo.txt"
    channels, template_channels = filter_source_urls(template_file)
    updateChannelUrlsM3U(channels, template_channels)
