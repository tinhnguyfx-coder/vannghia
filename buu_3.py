import os
import time
import json
import threading  # dùng threading thay cho multiprocessing

import random
from datetime import datetime

# Danh sách màu ngẫu nhiên (đặt ở đầu file, sau import random)
COLOR_LIST = [
    "#DB342E",  # đỏ
    "#15A85F",  # xanh lá
    "#F27806",  # cam
    "#F7B503",  # vàng
    "#FFFFFF",  # trắng
    "#000000"  # đen
]

# Thư viện Zalo giả định (giữ nguyên như file gốc của bạn)
from zlapi import ZaloAPI, ThreadType, Message
from zlapi.models import Mention, MultiMention, MessageStyle, MultiMsgStyle

# =========================
# Cấu hình hiển thị / helper
# =========================
UI_WIDTH = 70

class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def draw_box(title, lines, color=Colors.CYAN):
    print(color + "╔" + "═"*50 + "╗")
    print("║ " + title.center(48) + " ║")
    print("╠" + "═"*50 + "╣")
    for line in lines:
        print("║ " + line.ljust(48) + " ║")
    print("╚" + "═"*50 + "╝" + Colors.RESET)

def custom_print(msg):
    print(f"{Colors.YELLOW}{msg}{Colors.RESET}")

def read_file_content(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except:
        return ""

def read_list_file(file_path):
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except:
        return []

# =========================
# Helper TTL normalization
# =========================
# Một số API dùng TTL tính bằng milliseconds, một số bằng seconds. Ở đây
# ta chấp nhận người dùng nhập TTL theo *giây* (ví dụ: 10)
# - Nếu input < 1000 -> coi là giây, chuyển sang milliseconds (10 -> 10000)
# - Nếu input >= 1000 -> coi là đã là milliseconds, dùng nguyên
# Trả về None nếu TTL không hợp lệ hoặc == 0

def normalize_ttl_value(ttl):
    if ttl is None:
        return None
    try:
        t = int(ttl)
    except Exception:
        return None
    if t <= 0:
        return None
    # Nếu nhỏ hơn 1000 giả sử người dùng nhập giây -> chuyển sang ms
    if t < 1000:
        return t * 1000
    return t

# =========================
# Bot cơ bản (từ file gốc)
# =========================
class Bot(ZaloAPI):
    def __init__(self, imei, session_cookies, acc_index, delay, message_text, use_color=True, ttl=None):
        super().__init__("dummy_api_key", "dummy_secret_key", imei, session_cookies)
        self.acc_index = acc_index
        self.delay = delay
        self.stop_event = threading.Event()
        self.message_text = message_text
        self.use_color = use_color
        self.ttl = ttl

    def fetch_groups(self):
        groups_data = []
        try:
            all_groups = self.fetchAllGroups()
            for gid, _ in all_groups.gridVerMap.items():
                ginfo = super().fetchGroupInfo(gid)
                gname = ginfo.gridInfoMap[gid]["name"] if gid in ginfo.gridInfoMap else "Unknown"
                groups_data.append({"id": gid, "name": gname})
        except Exception as e:
            draw_box(f"[Acc {self.acc_index}] Lỗi lấy nhóm", [str(e)], Colors.RED)
        return groups_data

    def send_spam(self, group_id, group_name=None):
        text = self.message_text.strip()
        mention = Mention("-1", length=len(text), offset=0)
        style = MultiMsgStyle([
            MessageStyle(offset=0, length=10000, style="color", color="#0084FF", auto_format=False),
            MessageStyle(offset=0, length=10000, style="font", size="16", auto_format=False),
        ])
        try:
            while not self.stop_event.is_set():
                self.send(Message(text=text, mention=mention, style=style),
                          thread_id=group_id,
                          thread_type=ThreadType.GROUP,
                          ttl=self.ttl if self.ttl else None)
                custom_print(f"Đã spam tới nhóm {group_id}")
                time.sleep(self.delay)
        except Exception as e:
            custom_print(f"Lỗi khi spam: {e}")
    

def run_multi_acc():
    clear_screen()
    num_acc = int(input(" Nhập số lượng acc: ").strip())
    bots = []
    for i in range(num_acc):
        clear_screen()
        imei = input("Imei: ").strip()
        cookie_str = input("Cookie: ").strip()
        file_txt = input("File(.txt): ").strip()
        delay = int(input("Delay: ").strip() or "5")
        ttl_input = input("Ttl (giây, 0 = không): ").strip()
        ttl = int(ttl_input) if ttl_input.isdigit() and int(ttl_input) > 0 else None
        try:
            cookies = json.loads(cookie_str)
        except:
            continue
        message_text = read_file_content(file_txt)
        bot = Bot(imei, cookies, i+1, delay, message_text, ttl=ttl)
        bots.append(bot)
        groups = bot.fetch_groups()
        if not groups:
            continue
        print("\nDanh sách nhóm:")
        for idx, g in enumerate(groups, 1):
            print(f"{idx}. {g['name']} (ID: {g['id']})")
        choice_str = input(" Chọn nhóm: ").strip()
        choices = [int(x) for x in choice_str.split(",") if x.strip().isdigit()]
        for choice in choices:
            if 1 <= choice <= len(groups):
                gid = groups[choice-1]['id']
                gname = groups[choice-1]['name']
                threading.Thread(target=bot.send_spam, args=(gid,gname)).start()
    if not bots:
        draw_box("KẾT QUẢ", ["❌ Không có acc nào hợp lệ."], Colors.RED)
    while True: time.sleep(1)

# =========================
# TagBot (réo nhiều người)
# =========================
class TagBot(ZaloAPI):
    def __init__(self, imei=None, session_cookies=None):
        super().__init__("dummy_api_key", "dummy_secret_key", imei, session_cookies)
        self.running = False

    def fetchGroupInfo(self):
        try:
            all_groups = self.fetchAllGroups()
            group_list = []
            for group_id, _ in all_groups.gridVerMap.items():
                group_info = super().fetchGroupInfo(group_id)
                group_name = group_info.gridInfoMap[group_id]["name"]
                group_list.append({'id': group_id, 'name': group_name})
            return group_list
        except Exception as e:
            print(f"❌ Lỗi khi lấy danh sách nhóm: {e}")
            return []

    def fetchGroupMembers(self, group_id):
        try:
            group_info = super().fetchGroupInfo(group_id)
            mem_ver_list = group_info.gridInfoMap[group_id]["memVerList"]
            member_ids = [mem.split("_")[0] for mem in mem_ver_list]
            members = []
            for user_id in member_ids:
                try:
                    user_info = self.fetchUserInfo(user_id)
                    user_data = user_info.changed_profiles[user_id]
                    members.append({
                        'id': user_data['userId'],
                        'name': user_data['displayName']
                    })
                except Exception:
                    members.append({'id': user_id, 'name': f"[Không lấy được tên {user_id}]"})
            return members
        except Exception as e:
            print(f"❌ Lỗi khi lấy danh sách thành viên: {e}")
            return []

    def send_message_multi(self, thread_id, message_text, users):
        try:
            mentions = []
            formatted_message = (message_text or "").rstrip() + " "

            for uid in users:
                user_info = self.fetchUserInfo(uid)
                user_name = user_info.changed_profiles[uid]['displayName']

                tag_text = f"@{user_name}"
                offset = len(formatted_message)
                formatted_message += tag_text + " "
                mentions.append(Mention(uid=uid, length=len(tag_text), offset=offset, auto_format=False))

            multi_mention = MultiMention(mentions) if mentions else None

            self.send(
                Message(text=formatted_message, mention=multi_mention),
                thread_id=thread_id,
                thread_type=ThreadType.GROUP
            )
            print(f"✅ Đã gửi tin nhắn vào nhóm {thread_id}")
        except Exception as e:
            print(f"❌ Lỗi khi gửi: {e}")

    def send_message_all(self, thread_id, message_text):
        try:
            tag_text = "@All"
            formatted_message = (message_text or "").rstrip() + " " + tag_text

            offset = len(formatted_message) - len(tag_text)
            mention = Mention(uid="-1", length=len(tag_text), offset=offset, auto_format=False)
            multi_mention = MultiMention([mention])

            self.send(
                Message(text=formatted_message, mention=multi_mention),
                thread_id=thread_id,
                thread_type=ThreadType.GROUP
            )
            print(f"✅ Đã gửi @All vào nhóm {thread_id}")
        except Exception as e:
            print(f"❌ Lỗi khi gửi @All: {e}")

    def send_file_content(self, thread_id, filename, delay, users):
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                lines = [line.strip() for line in file.readlines() if line.strip()]

            if not lines:
                print("❌ File rỗng hoặc không có nội dung.")
                return

            self.running = True
            while self.running:
                for line in lines:
                    if not self.running:
                        break
                    if users == ["@all"]:
                        self.send_message_all(thread_id, line)
                    else:
                        self.send_message_multi(thread_id, line, users)
                    time.sleep(delay)

            print(f"✅ Hoàn thành gửi nội dung từ file {filename} vào nhóm {thread_id}")
        except FileNotFoundError:
            print(f"❌ Không tìm thấy file: {filename}")
        except Exception as e:
            print(f"❌ Lỗi khi đọc file hoặc gửi tin nhắn: {e}")

    def stop_sending(self):
        self.running = False
        print("🚦 Đã dừng gửi tin nhắn.")

# =========================
# TreongonBot (treo video + text, có thumb + font size)
# =========================
class TreongonBot(ZaloAPI):
    def __init__(self, api_key, secret_key, imei, session_cookies,
                 delay=5, message_text="", ttl=None,
                 media_source="videos.txt"):
        super().__init__(api_key, secret_key, imei, session_cookies)
        self.delay = delay
        self.message_text = message_text
        # lưu TTL nguyên bản (thường là giây) -> chuẩn hoá khi gửi
        self.ttl = int(ttl) if ttl is not None else None
        self.media_source = media_source
        self.running_flag = threading.Event()
        self.running_flag.set()
        self.thumb_url = None
        self.font_size = 40   # mặc định
        self.color_mode = 'y'  # mặc định: mỗi dòng 1 màu

    def spam_messages(self, thread_id, thread_type, ttl=None):
        while self.running_flag.is_set():
            try:
                # Gõ giả lập
                self.setTyping(thread_id, thread_type)
                time.sleep(4)

                # Gửi video từ videos.txt
                vids = read_list_file(self.media_source)
                if vids:
                    url = random.choice(vids)
                    thumb = self.thumb_url if self.thumb_url else ""
                    ttl_to_send = normalize_ttl_value(ttl if ttl is not None else self.ttl)
                    self.sendRemoteVideo(
                        url, thumb, duration="100000",
                        thread_id=thread_id, thread_type=thread_type,
                        width=1920, height=1080,
                        ttl=ttl_to_send
                    )

                # Gửi text với từng dòng có màu ngẫu nhiên
                if self.message_text:
                    lines = self.message_text.strip().splitlines()
                    styles = []
                    formatted_text = ""
                    offset = 0

                    if self.color_mode == 'n':
                        chosen_color = random.choice(COLOR_LIST)
                    for line in lines:
                        if self.color_mode == 'y':
                            color = random.choice(COLOR_LIST)
                        else:
                            color = chosen_color
                        line_text = line + "\n"
                        formatted_text += line_text

                        # style màu
                        styles.append(
                            MessageStyle(
                                offset=offset,
                                length=len(line_text),
                                style="color",
                                color=color,
                                auto_format=False
                            )
                        )
                        # style font
                        styles.append(
                            MessageStyle(
                                offset=offset,
                                length=len(line_text),
                                style="font",
                                size=str(self.font_size),
                                auto_format=False
                            )
                     )
                        offset += len(line_text)

                    style = MultiMsgStyle(styles)
                    mention = Mention("-1", length=len(formatted_text), offset=0)

                    ttl_to_send = normalize_ttl_value(ttl if ttl is not None else self.ttl)

                    self.send(Message(text=formatted_text, mention=mention, style=style),
                              thread_id=thread_id, thread_type=thread_type,
                              ttl=ttl_to_send)

                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"{Colors.CYAN}[{timestamp}] Treo Video + Ngôn file.txt -> {thread_id}{Colors.RESET}")

            except Exception as e:
                custom_print(f"Lỗi: {e}")

            time.sleep(self.delay)


# =========================
# TreongonTextBot (treo ngôn chỉ text, không video, không tag)
# =========================
class TreongonTextBot(ZaloAPI):
    def __init__(self, api_key, secret_key, imei, session_cookies,
                 delay=5, message_text="", ttl=None):
        super().__init__(api_key, secret_key, imei, session_cookies)
        self.delay = delay
        self.message_text = message_text
        self.ttl = int(ttl) if ttl is not None else None
        self.running_flag = threading.Event()
        self.running_flag.set()
        self.font_size = 40
        self.color_mode = 'y'  # mặc định: mỗi dòng 1 màu

    def spam_messages(self, thread_id, thread_type, ttl=None):
        while self.running_flag.is_set():
            try:
                if self.message_text:
                    lines = self.message_text.strip().splitlines()
                    styles = []
                    formatted_text = ""
                    offset = 0

                    if self.color_mode == 'n':
                        chosen_color = random.choice(COLOR_LIST)
                    for line in lines:
                        if self.color_mode == 'y':
                            color = random.choice(COLOR_LIST)
                        else:
                            color = chosen_color
                        line_text = line + "\n"
                        formatted_text += line_text

                        styles.append(
                            MessageStyle(
                                offset=offset,
                                length=len(line_text),
                                style="color",
                                color=color,
                                auto_format=False
                            )
                        )
                        styles.append(
                            MessageStyle(
                                offset=offset,
                                length=len(line_text),
                                style="font",
                                size=str(self.font_size),
                                auto_format=False
                            )
                        )
                        offset += len(line_text)

                    style = MultiMsgStyle(styles)
                    ttl_to_send = normalize_ttl_value(ttl if ttl is not None else self.ttl)

                    self.send(Message(text=formatted_text, style=style),
                              thread_id=thread_id, thread_type=thread_type,
                              ttl=ttl_to_send)

                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"{Colors.GREEN}[{timestamp}] Treo Ngôn Text -> {thread_id}{Colors.RESET}")

            except Exception as e:
                custom_print(f"Lỗi: {e}")

            time.sleep(self.delay)


def run_treongon_text():
    clear_screen()
    try:
        num_acc = int(input(" Nhập số lượng acc: ").strip())
    except:
        print("Số lượng acc không hợp lệ.")
        return

    bots = []
    for i in range(num_acc):
        imei = input("Imei: ").strip()
        cookie_str = input("Cookie: ").strip()
        try:
            cookies = json.loads(cookie_str)
        except:
            print("Cookie không hợp lệ, bỏ qua acc này.")
            continue

        file_txt = input("File(.txt): ").strip()
        message_text = read_file_content(file_txt)
        try:
            delay = int(input("Delay: ").strip() or "5")
        except:
            delay = 5

        ttl_input = input("Ttl (giây, 0 = không): ").strip()
        ttl = int(ttl_input) if ttl_input.isdigit() and int(ttl_input) > 0 else None

        bot = TreongonTextBot("api", "secret", imei, cookies, delay,
                              message_text, ttl)

        font_size_input = input("👉 Nhập size chữ (tối đa 500, mặc định 40): ").strip()
        font_size = int(font_size_input) if font_size_input.isdigit() else 40
        if font_size > 500:
            font_size = 500
        bot.font_size = font_size

        color_choice = input("👉 Chọn chế độ màu (y = mỗi dòng 1 màu, n = cả tin 1 màu): ").strip().lower()
        bot.color_mode = 'y' if color_choice == 'y' else 'n'

        bots.append(bot)

        groups = []
        try:
            all_groups = bot.fetchAllGroups()
            for gid, _ in all_groups.gridVerMap.items():
                ginfo = bot.fetchGroupInfo(gid)
                gname = ginfo.gridInfoMap[gid]["name"] if gid in ginfo.gridInfoMap else "Unknown"
                groups.append({"id": gid, "name": gname})
        except Exception as e:
            custom_print(f"Lỗi lấy nhóm: {e}")

        if not groups:
            print("Không có nhóm để chọn cho acc này.")
            continue

        print("\nDanh sách nhóm:")
        for idx, g in enumerate(groups, 1):
            print(f"{idx}. {g['name']} (ID: {g['id']})")
        choice_str = input(" Chọn nhóm (vd: 1,2,3): ").strip()
        choices = [int(x) for x in choice_str.split(",") if x.strip().isdigit()]
        for choice in choices:
            if 1 <= choice <= len(groups):
                gid = groups[choice-1]['id']
                threading.Thread(target=bot.spam_messages,
                                        args=(gid, ThreadType.GROUP, ttl), daemon=True).start()

    if not bots:
        draw_box("KẾT QUẢ", ["❌ Không có acc nào hợp lệ."], Colors.RED)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        for b in bots:
            try:
                b.running_flag.clear()
            except:
                pass
        print("\nĐã dừng Treo Ngôn Text.")

# =========================
# TreoAnhBot (giống Treo Video nhưng gửi bằng ảnh, auto tag all)
# =========================
class TreoAnhBot(ZaloAPI):
    def __init__(self, api_key, secret_key, imei, session_cookies,
                 delay=5, message_text="", ttl=None, image_folder="Gbao",
                 font_size=40, color_mode="y", mentions=None):
        super().__init__(api_key, secret_key, imei, session_cookies)
        self.delay = delay
        self.message_text = message_text
        self.ttl = int(ttl) if ttl is not None else None
        self.running_flag = threading.Event()
        self.running_flag.set()
        self.image_folder = image_folder
        self.font_size = font_size
        self.color_mode = color_mode  # 'y' = mỗi dòng 1 màu, 'n' = cả tin 1 màu
        self.mentions = mentions or []

    def spam_messages(self, thread_id, thread_type, ttl=None):
        while self.running_flag.is_set():
            try:
                # 🖼️ Gửi ảnh ngẫu nhiên từ thư mục Gbao
                if os.path.exists(self.image_folder):
                    images = [f for f in os.listdir(self.image_folder)
                              if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))]
                    if images:
                        img_file = random.choice(images)
                        img_path = os.path.join(self.image_folder, img_file)
                        ttl_to_send = normalize_ttl_value(ttl if ttl is not None else self.ttl)

                        # ❌ KHÔNG truyền mention ở đây (vì sendLocalImage không hỗ trợ)
                        self.sendLocalImage(img_path,
                                            thread_id=thread_id,
                                            thread_type=thread_type,
                                            ttl=ttl_to_send)

                # 📝 Gửi ngôn kèm style + tag all
                if self.message_text:
                    lines = self.message_text.strip().splitlines()
                    styles = []
                    formatted_text = ""
                    offset = 0

                    if self.color_mode == 'n':
                        chosen_color = random.choice(COLOR_LIST)

                    for line in lines:
                        color = random.choice(COLOR_LIST) if self.color_mode == 'y' else chosen_color
                        line_text = line + "\n"
                        formatted_text += line_text

                        styles.append(MessageStyle(offset=offset, length=len(line_text),
                                                   style="color", color=color, auto_format=False))
                        styles.append(MessageStyle(offset=offset, length=len(line_text),
                                                   style="font", size=str(self.font_size), auto_format=False))
                        offset += len(line_text)

                    style = MultiMsgStyle(styles)
                    ttl_to_send = normalize_ttl_value(ttl if ttl is not None else self.ttl)

                    multi_mention = None
                    if self.mentions:
                        multi_mention = MultiMention([
                            Mention(uid=uid, length=5, offset=len(formatted_text), auto_format=False)
                            for uid in self.mentions
                        ])

                    self.send(Message(text=formatted_text, style=style, mention=multi_mention),
                              thread_id=thread_id, thread_type=thread_type,
                              ttl=ttl_to_send)

                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"{Colors.MAGENTA}[{timestamp}] Treo Ảnh -> {thread_id}{Colors.RESET}")

            except Exception as e:
                custom_print(f"Lỗi khi gửi ảnh + ngôn: {e}")

            time.sleep(self.delay)

def run_treoanh():
    clear_screen()
    try:
        num_acc = int(input(" Nhập số lượng acc: ").strip())
    except:
        print("Số lượng acc không hợp lệ.")
        return

    bots = []
    for i in range(num_acc):
        imei = input("Imei: ").strip()
        cookie_str = input("Cookie: ").strip()
        try:
            cookies = json.loads(cookie_str)
        except:
            print("Cookie không hợp lệ, bỏ qua acc này.")
            continue

        file_txt = input("File ngôn (.txt): ").strip()
        message_text = read_file_content(file_txt)

        try:
            delay = int(input("Delay (giây): ").strip() or "5")
        except:
            delay = 5

        ttl_input = input("TTL (giây, 0 = không): ").strip()
        ttl = int(ttl_input) if ttl_input.isdigit() and int(ttl_input) > 0 else None

        font_size_input = input("👉 Nhập size chữ (tối đa 500, mặc định 40): ").strip()
        font_size = int(font_size_input) if font_size_input.isdigit() else 40
        if font_size > 500:
            font_size = 500

        color_choice = input("👉 Chọn chế độ màu (y = mỗi dòng 1 màu, n = cả tin 1 màu): ").strip().lower()
        color_mode = 'y' if color_choice == 'y' else 'n'

        bot_tmp = ZaloAPI("api", "secret", imei, cookies)

        # lấy danh sách nhóm
        groups = []
        try:
            all_groups = bot_tmp.fetchAllGroups()
            for gid, _ in all_groups.gridVerMap.items():
                ginfo = bot_tmp.fetchGroupInfo(gid)
                gname = ginfo.gridInfoMap[gid]["name"] if gid in ginfo.gridInfoMap else "Unknown"
                groups.append({"id": gid, "name": gname})
        except Exception as e:
            custom_print(f"Lỗi lấy nhóm: {e}")

        if not groups:
            print("Không có nhóm để chọn.")
            continue

        print("\nDanh sách nhóm:")
        for idx, g in enumerate(groups, 1):
            print(f"{idx}. {g['name']} (ID: {g['id']})")

        choice_str = input(" Chọn nhóm (vd: 1,2,3): ").strip()
        choices = [int(x) for x in choice_str.split(",") if x.strip().isdigit()]
        for choice in choices:
            if 1 <= choice <= len(groups):
                gid = groups[choice-1]['id']

                # ✅ Hỏi có tag all hay không
                tag_all_choice = input("👉 Có tag tất cả thành viên? (y/n): ").strip().lower()

                mentions = []
                if tag_all_choice == "y":
                    members = bot_tmp.fetchGroupInfo(gid).gridInfoMap[gid]["memVerList"]
                    mentions = [m.split("_")[0] for m in members]

                bot = TreoAnhBot("api", "secret", imei, cookies,
                                 delay=delay, message_text=message_text, ttl=ttl,
                                 image_folder="Gbao", font_size=font_size,
                                 color_mode=color_mode, mentions=mentions)

                bots.append(bot)
                threading.Thread(target=bot.spam_messages,
                                 args=(gid, ThreadType.GROUP, ttl), daemon=True).start()

    if not bots:
        draw_box("KẾT QUẢ", ["❌ Không có acc nào hợp lệ."], Colors.RED)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        for b in bots:
            try:
                b.running_flag.clear()
            except:
                pass
        print("\nĐã dừng Treo Ảnh.")

def run_tag_spam():
    clear_screen()
    imei = input("IMEI : ").strip()
    cookie_str = input("Cookie : ").strip()
    try:
        cookies = json.loads(cookie_str)
    except:
        print("❌ Cookie không hợp lệ.")
        return

    client = TagBot(imei, cookies)
    groups = client.fetchGroupInfo()
    if not groups:
        return

    lines = [f"{i+1}. {g['name']} - ID: {g['id']}" for i, g in enumerate(groups)]
    draw_box("DANH SÁCH NHÓM", lines, Colors.CYAN)

    choice_str = input("\n Nhập số nhóm muốn chọn (vd: 1,2,3): ")
    choices = [int(x) for x in choice_str.split(",") if x.strip().isdigit()]
    selected_groups = [groups[c-1] for c in choices if 1 <= c <= len(groups)]

    if not selected_groups:
        print("⚠️ Không chọn nhóm nào.")
        return

    filename = input("📄 Nhập tên file chứa tin nhắn (ví dụ: tag.txt): ").strip()
    try:
        delay = float(input("⏳ Nhập delay (giây, đề xuất 5-10): ").strip())
    except ValueError:
        print("⚠️ Delay không hợp lệ, mặc định = 5")
        delay = 5

    for group in selected_groups:
        members = client.fetchGroupMembers(group['id'])
        lines = [f"{i+1}. {m['name']} (ID: {m['id']})" for i, m in enumerate(members)]
        draw_box(f"THÀNH VIÊN NHÓM {group['name']}", lines, Colors.YELLOW)

        choice = input("Nhập số thành viên để tag (cách nhau bằng dấu phẩy, 0 để bỏ qua, all để @All): ").strip()
        if choice.lower() == "0":
            users = []
        elif choice.lower() == "all":
            users = ["@all"]
        else:
            users = [members[int(x.strip()) - 1]['id'] for x in choice.split(",") if x.strip().isdigit()]

        send_thread = threading.Thread(target=client.send_file_content, args=(group['id'], filename, delay, users))
        send_thread.daemon = True
        send_thread.start()

    print(f"🚀 Bắt đầu spam từ file {filename} vào {len(selected_groups)} nhóm với delay {delay} giây...")
    input("Nhấn Enter để quay lại menu...")


# =========================
# TreongonBot runner
# =========================

def run_treongonbot():
    global COLOR_MODE
    
    clear_screen()
    try:
        num_acc = int(input(" Nhập số lượng acc: ").strip())
    except:
        print("Số lượng acc không hợp lệ.")
        return

    bots = []
    for i in range(num_acc):
        imei = input("Imei: ").strip()
        cookie_str = input("Cookie: ").strip()
        try:
            cookies = json.loads(cookie_str)
        except:
            print("Cookie không hợp lệ, bỏ qua acc này.")
            continue

        file_txt = input("File(.txt): ").strip()
        message_text = read_file_content(file_txt)
        try:
            delay = int(input("Delay: ").strip() or "5")
        except:
            delay = 5

        ttl_input = input("Ttl (giây, 0 = không): ").strip()
        ttl = int(ttl_input) if ttl_input.isdigit() and int(ttl_input) > 0 else None

        # Sử dụng file videos.txt cố định (tạo file này trong cùng thư mục)
        media_source = "videos.txt"

        # Nhập URL ảnh bìa và size chữ
        thumb_url = input("👉 Nhập URL ảnh làm bìa video: ").strip()
        font_size_input = input("👉 Nhập size chữ (tối đa 500, mặc định 40): ").strip()
        font_size = int(font_size_input) if font_size_input.isdigit() else 40
        if font_size > 500:
            font_size = 500

        # Khởi tạo bot (api/secret giữ dummy như trước)
        bot = TreongonBot("api", "secret", imei, cookies, delay,
                          message_text, ttl, media_source=media_source)
        bot.thumb_url = thumb_url
        bot.font_size = font_size

        # Hỏi chọn chế độ màu: y = mỗi dòng, n = cả tin 1 màu
        color_choice = input("👉 Chọn chế độ màu (y = mỗi dòng 1 màu, n = cả tin 1 màu): ").strip().lower()
        bot.color_mode = 'y' if color_choice == 'y' else 'n'


        bots.append(bot)

        # Lấy danh sách nhóm và hiển thị
        groups = []
        try:
            all_groups = bot.fetchAllGroups()
            for gid, _ in all_groups.gridVerMap.items():
                ginfo = bot.fetchGroupInfo(gid)
                gname = ginfo.gridInfoMap[gid]["name"] if gid in ginfo.gridInfoMap else "Unknown"
                groups.append({"id": gid, "name": gname})
        except Exception as e:
            custom_print(f"Lỗi lấy nhóm: {e}")

        if not groups:
            print("Không có nhóm để chọn cho acc này.")
            continue

        print("\nDanh sách nhóm:")
        for idx, g in enumerate(groups, 1):
            print(f"{idx}. {g['name']} (ID: {g['id']})")
        choice_str = input(" Chọn nhóm (vd: 1,2,3): ").strip()
        choices = [int(x) for x in choice_str.split(",") if x.strip().isdigit()]
        for choice in choices:
            if 1 <= choice <= len(groups):
                gid = groups[choice-1]['id']
                threading.Thread(target=bot.spam_messages,
                                        args=(gid, ThreadType.GROUP, ttl), daemon=True).start()

    if not bots:
        draw_box("KẾT QUẢ", ["❌ Không có acc nào hợp lệ."], Colors.RED)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        for b in bots:
            try:
                b.running_flag.clear()
            except:
                pass
        print("\nĐã dừng Treo Video.")

# =========================
# Menu chính
# =========================
def main_menu():
    while True:
        clear_screen()
        draw_box("ZALO TOOL MENU", [
            "1. 🚀 Treo Ngôn",
            "2. 🏷️ Réo Nhiều Người",
            "3. 🎞️ Treo Video",
            "4. 📝 Treo Ngôn 5 màu (không tag)",
            "5. 🖼️ Treo Ảnh",
            "0. ❌ Thoát",
            "Tool By Khai Minh"
        ], Colors.CYAN)
        choice = input("👉 Chọn chức năng: ").strip()
        if choice == "1":
            run_multi_acc()
        elif choice == "2":
            run_tag_spam()
        elif choice == "3":
            run_treongonbot()
        elif choice == "4":
            run_treongon_text()
        elif choice == "5":
            run_treoanh()
        elif choice == "0":
            break
        else:
            input("⚠️ Sai lựa chọn, nhấn Enter thử lại...")

# =============================
# Bảo vệ bằng mật khẩu
# =============================

def print_success_message():
    message = f"╭{'─'*50}╮\n│ Đúng Mật Khẩu!Welcome To Tools By Gbao! {' '*(14)}│\n╰{'─'*50}╯"
    print(message)

def print_loading_system():
    message = "Đang tiến hành vào hệ thống"
    print(message, end='', flush=True)
    for _ in range(5):
        print(f".", end='', flush=True)
        time.sleep(0.5)  
    print()  
    time.sleep(1)

def check_password():
    print(r"""
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
                   _ooOoo_
                  o8888888o
                  88" . "88
                  (| -_- |)
                  O\  =  /O
               ____/`---'\____
             .'  \\|     |//  `.
            /  \\|||  :  |||//  \
           /  _||||| -:- |||||-  \
           |   | \\\  -  /// |   |
           | \_|  ''\---/''  |   |
           \  .-\__  `-`  ___/-. /
         ___`. .'  /--.--\  `. . __
      ."" '<  `.___\_<|>_/___.'  >'"".
     | | :  `- \`.;`\ _ /`;.`/ - ` : | |
     \  \ `-.   \_ __\ /__ _/   .-` /  /
======`-.____`-.___\_____/___.-`____.-'======
                   `=---='
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  PHẬT ĐỘ, NHẬP MẬT KHẨU ĐỂ ĐƯỢC TU TÂM!
            DEVELOPER: Mai Khai Minh
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
""")

    password = "kminh"
    attempts = 3

    while attempts > 0:
        input_pass = input("\n🔐 Nhập mật khẩu để vào tool: ").strip()
        
        if input_pass == password:
            print_success_message()
            print_loading_system()  
            return True
        else:
            attempts -= 1
            if attempts > 0:
                print(f"\n❌ Mật Khẩu Sai !!! Còn {attempts} lần nhập lại")
            else:
                print("\n🗯️ Hãy Inbox Ngay Kminh Để Được Cung Cấp Mật Khẩu| Zalo: 0358005291 | Tool By Kminh")
                print(" Sai mật khẩu rồi, tool sẽ tắt trong 3 giây sau...")
                for i in range(3, 0, -1):
                    print(f" {i}...")
                    time.sleep(1)
                sys.exit()
    return False


# =============================
# Main
# =============================
if __name__ == "__main__":
    if check_password():
        main_menu()
