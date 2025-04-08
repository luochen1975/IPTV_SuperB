import os
from datetime import datetime
import requests
from ipaddress import ip_address
import logging

# 配置日志
logging.basicConfig(filename='fetch_channels.log', level=logging.ERROR)

def is_ipv6(url):
    try:
        start = url.find('[') + 1
        end = url.find(']')
        if start > 0 and end > start:
            ip = url[start:end]
            ip_address(ip)
            return True
    except ValueError:
        pass
    return False

def sort_and_filter_urls(urls, written_urls):
    sorted_urls = sorted(urls, key=lambda x: x[1])
    return [url for url in sorted_urls if url[0] not in written_urls]

def add_url_suffix(url, index, total_urls, ip_version):
    return f"{url}${ip_version}•线路{index}"

def write_to_files(f_m3u, f_txt, category, channel_name, index, new_url, response_time, logo_url):
    # 写入M3U和TXT文件。
    if not logo_url:
        logo_url = f"https://gitee.com/IIII-9306/PAV/raw/master/logos/{channel_name}.png"
    f_m3u.write(f"#EXTINF:-1 tvg-id=\"{index}\" tvg-name=\"{channel_name}\" tvg-logo=\"{logo_url}\" group-title=\"{category}\" tvg-response-time=\"{response_time:.2f}\",{channel_name}\n")
    f_m3u.write(new_url + "\n")
    f_txt.write(f"{channel_name},{new_url},{response_time:.2f},{logo_url}\n")

def updateChannelUrlsM3U(channels, template_channels):
    # 更新频道URL到M3U和TXT文件中。
    written_urls_ipv4 = set()
    written_urls_ipv6 = set()

    current_date = datetime.now().strftime("%Y-%m-%d")
    for group in config.announcements:
        for announcement in group['entries']:
            if announcement['name'] is None:
                announcement['name'] = current_date

    output_path = 'output'
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    with open(os.path.join(output_path, "live_ipv4.m3u"), "w", encoding="utf-8") as f_m3u_ipv4, \
            open(os.path.join(output_path, "live_ipv4.txt"), "w", encoding="utf-8") as f_txt_ipv4, \
            open(os.path.join(output_path, "live_ipv6.m3u"), "w", encoding="utf-8") as f_m3u_ipv6, \
            open(os.path.join(output_path, "live_ipv6.txt"), "w", encoding="utf-8") as f_txt_ipv6:

        f_m3u_ipv4.write(f"""#EXTM3U x-tvg-url={",".join(f'"{epg_url}"' for epg_url in config.epg_urls)}\n""")
        f_m3u_ipv6.write(f"""#EXTM3U x-tvg-url={",".join(f'"{epg_url}"' for epg_url in config.epg_urls)}\n""")

        for group in config.announcements:
            f_txt_ipv4.write(f"{group['channel']},#genre#\n")
            f_txt_ipv6.write(f"{group['channel']},#genre#\n")
            for announcement in group['entries']:
                f_m3u_ipv4.write(f"""#EXTINF:-1 tvg-id="1" tvg-name="{announcement['name']}" tvg-logo="{announcement['logo']}" group-title="{group['channel']}",{announcement['name']}\n""")
                f_m3u_ipv4.write(f"{announcement['url']}\n")
                f_txt_ipv4.write(f"{announcement['name']},{announcement['url']}\n")
                f_m3u_ipv6.write(f"""#EXTINF:-1 tvg-id="1" tvg-name="{announcement['name']}" tvg-logo="{announcement['logo']}" group-title="{group['channel']}",{announcement['name']}\n""")
                f_m3u_ipv6.write(f"{announcement['url']}\n")
                f_txt_ipv6.write(f"{announcement['name']},{announcement['url']}\n")

        for category, channel_list in template_channels.items():
            f_txt_ipv4.write(f"{category},#genre#\n")
            f_txt_ipv6.write(f"{category},#genre#\n")
            if category in channels:
                for channel_name in channel_list:
                    if channel_name in channels[category]:
                        sorted_urls_ipv4 = [url for url in sort_and_filter_urls(channels[category][channel_name], written_urls_ipv4) if not is_ipv6(url[0])]
                        sorted_urls_ipv6 = [url for url in sort_and_filter_urls(channels[category][channel_name], written_urls_ipv6) if is_ipv6(url[0])]

                        total_urls_ipv4 = len(sorted_urls_ipv4)
                        total_urls_ipv6 = len(sorted_urls_ipv6)

                        for index, (url, response_time, logo_url) in enumerate(sorted_urls_ipv4, start=1):
                            new_url = add_url_suffix(url, index, total_urls_ipv4, "IPV4")
                            write_to_files(f_m3u_ipv4, f_txt_ipv4, category, channel_name, index, new_url, response_time, logo_url)

                        for index, (url, response_time, logo_url) in enumerate(sorted_urls_ipv6, start=1):
                            new_url = add_url_suffix(url, index, total_urls_ipv6, "IPV6")
                            write_to_files(f_m3u_ipv6, f_txt_ipv6, category, channel_name, index, new_url, response_time, logo_url)

        f_txt_ipv4.write("\n")
        f_txt_ipv6.write("\n")

def fetch_channels():
    channels = {}
    for url in config.source_urls:
        print(f"Fetching source: {url}")  # 添加调试信息
        try:
            response = requests.get(url)
            print(f"Response status code for {url}: {response.status_code}")  # 添加调试信息
            if response.status_code == 200:
                lines = response.text.splitlines()
                current_category = None
                for line in lines:
                    if line.endswith("#genre#"):
                        current_category = line.split(',')[0]
                        if current_category not in channels:
                            channels[current_category] = {}
                    elif ',' in line:
                        parts = line.split(',')
                        print(f"Parsing line: {line}, parts: {parts}")  # 添加调试信息
                        if len(parts) >= 3:
                            channel_name = parts[0]
                            url = parts[1]
                            response_time = float(parts[2]) if len(parts) > 2 and parts[2].replace('.', '', 1).isdigit() else 0
                            logo_url = parts[3] if len(parts) > 3 else None
                            if any(blacklist in url for blacklist in config.url_blacklist):
                                continue
                            if channel_name not in channels[current_category]:
                                channels[current_category][channel_name] = []
                            channels[current_category][channel_name].append((url, response_time, logo_url))
        except Exception as e:
            logging.error(f"Error fetching {url}: {e}")
    return channels

if __name__ == "__main__":
    import config
    channels = fetch_channels()
    template_channels = {}  # 可以根据需要添加模板频道
    updateChannelUrlsM3U(channels, template_channels)    
