import os
import datetime
import shutil
import requests
import textwrap
import base64
import json
import PyPDF2
import pyperclip
import markdown
# from cookielogin import CookieLogin
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from pathlib import Path
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
from jinja2 import Template

# 输入今日任务
def fetch_task(q):
    # 获取今天的日期
    today = datetime.date.today()
    # 将日期转换为字符串
    today_str = today.strftime("%Y-%m-%d")
    # 1=留学话题；2移民话题；4=历史上的今天；5=读书话题；6=Github热点
    if q in ["1","2"]:
        working_task = ("",[],[],[],"","","./archive/zhi/","cookie_xhs_zhi.json")
    elif q == "4":
        working_task = (today_str,[],[],[],"","","./archive/share/today/","cookie_xhs_share.json")
    elif q == "5":
        working_task = (today_str,[],[],[],"","","./archive/share/cc/","cookie_xhs_share.json")
    elif q == "6":
        working_task = (today_str,[],[],[],"","","./archive/share/hh/","cookie_xhs_share.json")
    # return顺序 pic_title,pic_subtitles,pic_bodies,names,title,desc,archive_dir, acct_info 
    return working_task

# gpt part 获取今日新闻
def fetch_news(q):
    # 发送请求并获取新闻
    if q == "4":
        api_url = "https://todayhot.ai4uo.com/history"
    elif q == "6":
        api_url = "https://todayhot.ai4uo.com/hellogithub"
    response = requests.get(api_url)
    data = response.json()['data']
    # 获取全部热点
    if q == "4":
        title_str = [item["title"] for item in data if "什么" not in item["title"] and "逝" not in item["title"]]
        desc_str = [item["desc"] for item in data if "什么" not in item["title"] and "逝" not in item["title"]]
    elif q == "6":
        title_str = [item["title"] for item in data if len(item["title"]) < 13]
        desc_str = [item["desc"] for item in data if len(item["title"]) < 13]
    return title_str, desc_str

# 读取知识库
def reading_kb(kb_dir):
    # 定义目录路径
    used_dir = kb_dir + 'used/'

    # 确保used目录存在
    if not os.path.exists(used_dir):
        os.makedirs(used_dir)

    # 获取kb目录下所有.json文件的列表，并按名称排序
    json_files = sorted([f for f in os.listdir(kb_dir) if f.endswith('.json')])

    # 检查是否有.json文件
    if json_files:
        # 选择第一个.json文件
        first_json_file = json_files[0]
        file_path = os.path.join(kb_dir, first_json_file)

        # 读取数据
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        # 移动文件到used目录
        shutil.move(file_path, os.path.join(used_dir, first_json_file))
    else:
        print("在kb目录下没有找到.json文件。")
    return data.values()
# gpt part 生成正文
def generating(content, prompt_path):
    client = OpenAI(
        api_key=os.getenv('API_KEY_ZHIPU'),
        base_url=os.getenv('URL_ZHIPU'), 
    )
    # 定义提示词
    with open(prompt_path, 'r', encoding='utf-8') as file:
        your_prompt = file.read()
    your_prompt = your_prompt + '\n'.join(content)
    try:
        completion = client.chat.completions.create(
            model='glm-4', # glm有期限  
            messages = [
                {
                    "role": "user",
                    "content": your_prompt
                }
            ],
        )
        print(completion.choices[0].message.content)
        anwser = completion.choices[0].message.content
    except Exception as e:
        print("提示", e)
        anwser = "敏感词censored by glm"
    print("大模型工作中，请稍等片刻")
    return anwser
# gpt part 标题去标点
def shorten_topic(content, prompt_path):
    client = OpenAI(
        api_key=os.getenv('API_KEY_SPARKO'),
        base_url=os.getenv('URL_SPARK'), 
    )
    # 定义提示词
    with open(prompt_path, 'r', encoding='utf-8') as file:
        your_prompt = file.read()
    your_prompt = your_prompt + '\n'.join(content)
    try:
        completion = client.chat.completions.create(
            model = "4.0Ultra",
            messages = [
                {"role": "user", "content": your_prompt}
            ],
            # temperature = 0.3,
        )
        anwser = completion.choices[0].message.content
        print(completion.choices[0].message.content)
    except Exception as e:
        print("提示", e)
        anwser = content
    print("大模型工作中，请稍等片刻")
    return anwser

def writing_xhs_title(content, prompt_path):
    client = OpenAI(
        api_key=os.getenv('API_KEY_KIMI'),
        base_url=os.getenv('URL_KIMI'), 
    )
    # 定义提示词
    with open(prompt_path, 'r', encoding='utf-8') as file:
        your_prompt = file.read()
    your_prompt = your_prompt + '\n'.join(content)
    try:
        completion = client.chat.completions.create(
            model="moonshot-v1-8k",  #每分钟3次调用
            messages=[
                {
                    "role": "user",
                    "content": your_prompt
                }
            ],
        )
        print(completion.choices[0].message.content)
        answer = completion.choices[0].message.content
        answer = answer.split("。")
    except Exception as e:
        print("提示", e)
        answer = "敏感词censored by moonshot"
    return answer[0]

def writing_xhs_desc(content, prompt_path):
    client = OpenAI(
        api_key=os.getenv('API_KEY_KIMI'),
        base_url=os.getenv('URL_KIMI'), 
    )
    # 定义提示词
    with open(prompt_path, 'r', encoding='utf-8') as file:
        your_prompt = file.read()
    your_prompt = your_prompt + '\n'.join(content)
    try:
        completion = client.chat.completions.create(
            model="moonshot-v1-8k",  
            messages=[
                {
                    "role": "user",
                    "content": your_prompt
                }
            ],
        )
        answer = completion.choices[0].message.content
    except Exception as e:
        print("提示", e)
        answer = "敏感词censored by moonshot"
    return answer

# poster将文本拆分成若干小段
def split_text(text, segment_length):
    segments = []
    current_segment = ""
    for char in text:
        if char == '\n':
            # 如果遇到回车符，则将当前段添加到列表中，并开始新的一段
            segments.append(current_segment)
            current_segment = ""
        elif len(current_segment) >= segment_length:
            # 如果当前段长度达到指定长度，则将其添加到列表中，并开始新的一段
            segments.append(current_segment)
            current_segment = char
        else:
            # 否则，将字符添加到当前段
            current_segment += char
    # 将最后一个段添加到列表中
    segments.append(current_segment)
    return segments
# poster将文本拆分成若干小段-windows only
def splitting_text(text):
  html_template = """
  <!DOCTYPE html>
  <html lang="zh-CN">
  <head>
  <title>body</title>
  <style>
    @font-face {{
      font-family: 'xyjxs';
      src: url('./fonts/xyjxs.ttf') format('truetype');
      font-style: normal;
    }}
    body, html {{
      margin: 0;
      padding: 0;
    }}
    .container {{
      width: 720px;
      height: 1280px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }}
    .pic_body {{
      font-size: 50px; /* 设置字号为38 */
      width: 580px; /* 设置宽度为80% */
      height: 700px; /* 设置高度为500px */
      color: black; /* 设置颜色为黑色 */
      text-align: justify; /* 两端对齐 */
      font-family: 'xyjxs', sans-serif; /* 设置字体为Noto Sans SC */
      position: absolute;
      top: 300px; /* 设置垂直位置为190 */
    }}
  </style>
  </head>
  <body>
  <div class="container">
    <div id="pic_body" class="pic_body">{}</div>
  </div>
  </body>
  </html>
  """

  text1 = text.replace('\n', '<br>')
  html_with_text = html_template.format(text1)
  # 将HTML内容写入文件
  with open('body.html', 'w', encoding='utf-8') as file:
      file.write(html_with_text)
  # 打印HTML文件
  save_path = os.getcwd() # 当前文件所在的文件夹路径
  driver_path = os.getenv('CHROME_DRIVER_PATH')
  service = Service(driver_path)
  options = Options()
  settings = {
      "recentDestinations": [{
          "id": "Save as PDF",
          "origin": "local",
          "account": ""
      }],
      "selectedDestinationId": "Save as PDF",
      "version": 2,  # 另存为pdf，1 是默认打印机
      "isHeaderFooterEnabled": False,  # 是否勾选页眉和页脚
      "isCssBackgroundEnabled": True,  # 是否勾选背景图形
      "mediaSize": {
          "height_microns": 297000,
          "name": "ISO_A4",
          "width_microns": 210000,
          "custom_display_name": "A4",
      },
  }
  prefs = {
      'printing.print_preview_sticky_settings.appState': json.dumps(settings),
      'savefile.default_directory': save_path,
  }
  # options.add_argument('--headless')
  options.add_argument('--enable-print-browser') # 这一行试了，可用可不用
  options.add_argument('--kiosk-printing')  # 静默打印，无需用户点击打印页面的确定按钮
  options.add_experimental_option('prefs', prefs)
  driver = webdriver.Chrome(options=options, service=service)
  
  html_file_path = Path(save_path, 'body.html')
  driver.get(f'file://{html_file_path}')
  driver.execute_script(f'document.title="body.pdf";window.print();')
  # driver.execute_script('window.print();')
  sleep(3) 
  
  # 打开PDF文件
  with open("body.pdf", 'rb') as file:
      reader = PyPDF2.PdfReader(file)
      # 获取PDF文件的页数
      num_pages = len(reader.pages)
      your_segment = []
      # 提取每一页的文本
      for page_num in range(num_pages):
          page = reader.pages[page_num]
          your_segment.extend(page.extract_text().splitlines())
 
  if os.path.exists("body.pdf"):
    # 删除文件
    os.remove("body.pdf")
    os.remove("body.html")

  return your_segment
# poster模板选择
def choosing_picture_template(temp_num, bg_dir, font_dir):
    if temp_num == "1":
        # 背景图片文件路径-小护照的留学图-封面尺寸
        bg_image_path = bg_dir + 'bg-edu02.png'
        # 格式设定
        word_number = 17
        line_number = 11
        # 位置参数
        title_xy = (0, 200)
        subtitle_xy = (0, 590)
        text_xy = (0, 720)
        # 字体文件路径——需要描边升级
        text_font_path = font_dir + 'msyh.ttc'
        text_size = 50
        text_color = (0, 0, 0, 255)
        title_font_path = font_dir +'ceym.ttf'
        title_size = 120
        title_color = (255, 255, 255, 225)
        subtitle_font_path = font_dir + 'msyh.ttc'
        subtitle_size = 60
        subtitle_color = (255, 255, 255, 225)
        date_required = False
    elif temp_num == "2":
        # 背景图片文件路径-悉尼大桥的移民图-封面尺寸
        bg_image_path = bg_dir + 'bg-imm04.png'
        # 格式设定
        word_number = 18
        line_number = 10
        # 位置参数
        title_xy = (60, 540)
        subtitle_xy = (0, 670)
        text_xy = (0, 750)
        # 字体文件路径-需要渐变升级，底色升级
        text_font_path = font_dir + 'syst.otf'
        text_size = 50
        text_color = (33, 39, 79, 255)
        title_font_path = font_dir + 'SourceHanSansCNHeavy.otf'
        title_size = 78
        title_color = (255, 208, 47, 255)
        subtitle_font_path = font_dir + 'SourceHanSansRegular.otf'
        subtitle_size = 60
        subtitle_color = (0, 0, 0, 255)
        date_required = False
    elif temp_num == "3":
        # 背景图片文件路径-今日历史衍生图-还需要调整背景图
        bg_image_path = bg_dir + 'bg-imm02.png'
        # 格式设定
        word_number = 14
        line_number = 14
        # 位置参数
        title_xy = (0, 100)
        subtitle_xy = (0, 320)
        text_xy = (0, 470)
        # 字体文件路径
        text_font_path = font_dir + 'xyjxs.ttf'
        text_size = 70
        text_color = (0, 0, 0, 255)
        title_font_path =font_dir + 'ceym.ttf'
        title_size = 110
        title_color = (0, 0, 0, 255)
        subtitle_font_path = font_dir + 'ceym.ttf'
        subtitle_size = 80
        subtitle_color = (0, 0, 0, 255)
        date_required = False
    elif temp_num == "4":
        # 背景图片文件路径-历史上的今天
        bg_image_path = bg_dir + 'bg-hist.png'
        # 格式设定
        word_number = 17
        line_number = 14
        # 位置参数
        title_xy = (0, 1400)
        subtitle_xy = (0, 320)
        text_xy = (0, 470)
        # 字体文件路径
        text_font_path = font_dir + 'xyjxs.ttf'
        text_size = 70
        text_color = (0, 0, 0, 255)
        title_font_path =font_dir + 'ceym.ttf'
        title_size = 10
        title_color = (0, 0, 0, 0)
        subtitle_font_path = font_dir + 'ceym.ttf'
        subtitle_size = 80
        subtitle_color = (0, 0, 0, 255)
        date_required = True
    elif temp_num == "5":
        # 背景图片文件路径-代码ppt
        bg_image_path = bg_dir + 'bg-cc.png'
        # 格式设定
        word_number = 10
        line_number = 13
        # 位置参数
        title_xy = (0, 1100)
        subtitle_xy = (0, 195)
        text_xy = (0, 300)
        # 字体文件路径
        text_font_path = font_dir + 'xyjxs.ttf'
        text_size = 48
        text_color = (0, 0, 0, 255)
        title_font_path =font_dir + 'ceym.ttf'
        title_size = 30
        title_color = (0, 0, 0, 0)
        subtitle_font_path = font_dir + 'ceym.ttf'
        subtitle_size = 70
        subtitle_color = (0, 0, 0, 255)
        date_required = False
    elif temp_num == "6":
        # 背景图片文件路径
        bg_image_path = bg_dir + 'bg-hh.png'
        # 格式设定
        word_number = 17
        line_number = 14
        # 位置参数
        title_xy = (0, 1400)
        subtitle_xy = (0, 320)
        text_xy = (0, 470)
        # 字体文件路径
        text_font_path = font_dir + 'xyjxs.ttf'
        text_size = 70
        text_color = (0, 0, 0, 255)
        title_font_path =font_dir + 'ceym.ttf'
        title_size = 10
        title_color = (0, 0, 0, 0)
        subtitle_font_path = font_dir + 'ceym.ttf'
        subtitle_size = 80
        subtitle_color = (0, 0, 0, 255)
        date_required = True
    return (bg_image_path, date_required,              
            title_xy, title_font_path, title_size, title_color, 
            subtitle_xy, subtitle_font_path, subtitle_size, subtitle_color,
            text_xy, text_font_path, text_size, text_color), word_number, line_number
# poster创建并保存背景图
def create_post(element01, element02, element03,
                bg, date_required,
                element01_xy, element01_font_path, element01_size, element01_color, 
                element02_xy, element02_font_path, element02_size, element02_color,
                element03_xy, element03_font_path, element03_size, element03_color
):
    # 打开背景图片
    bg_image = Image.open(bg).convert("RGBA")
    
    # 创建一个ImageDraw对象
    draw = ImageDraw.Draw(bg_image)
    
    # 加载字体
    element01_font = ImageFont.truetype(element01_font_path, element01_size)
    element02_font = ImageFont.truetype(element02_font_path, element02_size)
    element03_font = ImageFont.truetype(element03_font_path, element03_size)
    date_font = ImageFont.truetype('./fonts/Monoton-Regular-2.ttf', 150)
    
    # 绘制主标题
    if element01_xy[1] == 200:
        element01 = textwrap.fill(element01, width=7)
    bbox = draw.textbbox((0, 0), element01, font=element01_font)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    if element01_xy[0] == 0: # 如果不指定x坐标，则居中显示
        x = (bg_image.width - text_width) // 2
        y = element01_xy[1]
    else:
        x = element01_xy[0]
        y = element01_xy[1]
    if element01_xy[1] < 1000: # 如果标题变水印，则不加阴影
        draw.text((x+5, y+5), element01, font=element01_font, fill=(0, 0, 0, 255))
    if element01_xy[1] == 200: # 如果是模板1，则描边+折行
        draw.text((x, y), element01, font=element01_font, fill=element01_color, stroke_width=2, stroke_fill='blue') #加了描边
    else:
        draw.text((x, y), element01, font=element01_font, fill=element01_color)
        
    # 绘制副标题
    bbox = draw.textbbox((0, 0), element02, font=element02_font)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    if element02_xy[0] == 0:
        x = (bg_image.width - text_width) // 2
        y = element02_xy[1]
    else:
        x = element02_xy[0]
        y = element02_xy[1]
    draw.text((x, y), element02, font=element02_font, fill=element02_color)
    
    # 绘制正文
    bbox = draw.textbbox((0, 0), element03, font=element03_font)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    if element03_xy[0] == 0:
        x = (bg_image.width - text_width) // 2
        y = element03_xy[1]
    else:
        x = element03_xy[0]
        y = element03_xy[1]
    draw.text((x, y), element03, font=element03_font, fill=element03_color)

    # 绘制日期
    if date_required:
        date = datetime.datetime.now()
        draw.text((200, 20), date.strftime('%d'), font=date_font, fill=(0, 0, 128, 255))
        draw.text((200, 120), date.strftime('%m'), font=date_font, fill=(0, 128, 0, 255))

    return bg_image
# poster创建并保存背景图
def creating_longpost(title, subtitle, body, temp_num):
    
    data2 = [{
    'title': title,
    'subtitles': subtitle,
    'bodies': body
    }] 
    
    if temp_num == "4":
        html_template_path = './html/template-hist.html'
    elif temp_num == "6":
        html_template_path = './html/template-hh.html'
    elif temp_num == "5":
        html_template_path = './html/template-cc.html'
    # 读取HTML模板文件
    with open(html_template_path, 'r', encoding='utf-8') as file:
        template = Template(file.read())

    # 渲染模板
    html_content = template.render(data=data2)

    # 将HTML内容写入文件
    with open('./tmp/working.html', 'w', encoding='utf-8') as file:
        file.write(html_content)

    # 设置HTML文件路径
    html_file_path = Path('./tmp/working.html').resolve()

    # 设置输出图片路径
    working_image_path = Path('./tmp/houtput.png')

    # 设置Chrome选项
    driver_path = os.getenv('CHROME_DRIVER_PATH')
    service = Service(driver_path)
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 无头模式，不显示浏览器窗口

    # 启动Chrome浏览器
    driver = webdriver.Chrome(options=chrome_options, service=service)

    # 打开HTML文件
    driver.get(f'file://{html_file_path}')

    # 设置浏览器窗口大小以适应网页高度
    driver.maximize_window()
    sleep(1)  # 等待页面加载完成
    
    # 获取页面截图
    screenshot = driver.execute_cdp_cmd("Page.captureScreenshot", {"format": "png", "fromSurface": True, "captureBeyondViewport": True})
    
    with open(working_image_path, 'wb') as f:
        img = base64.b64decode(screenshot['data'])
        f.write(img)
    
    # 关闭浏览器
    driver.quit()

    #return Image.open(working_image_path)
# poster创建并保存背景图
def creating_post(title, subtitle, body, temp_num, output_dir):
    
    data = [{
    'title': title,
    'subtitles': subtitle,
    'bodies': body
    }]
    if temp_num == "4":
        html_template_path = './html/template-hist.html'
    elif temp_num == "6":
        html_template_path = './html/template-hh.html'
    elif temp_num == "1":
        html_template_path = './html/template-edu02.html'
    # 读取HTML模板文件
    with open(html_template_path, 'r', encoding='utf-8') as file:
        template = Template(file.read())

    # 渲染模板
    html_content = template.render(data=data, render_markdown=markdown.markdown)
    # 设置HTML文件路径
    html_file_path = Path('./tmp/working.html').resolve()
    # 将HTML内容写入文件
    with open(html_file_path, 'w', encoding='utf-8') as file:
        file.write(html_content)

    # 设置输出图片路径
    working_image_path = os.path.join(output_dir, f"{subtitle.rstrip()}.png") 

    # 设置Chrome选项
    driver_path = os.getenv('CHROME_DRIVER_PATH')
    service = Service(driver_path)
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 无头模式，不显示浏览器窗口

    # 启动Chrome浏览器
    driver = webdriver.Chrome(options=chrome_options, service=service)

    # 打开HTML文件
    driver.get(f'file://{html_file_path}')

    # 设置浏览器窗口大小以适应网页高度
    driver.maximize_window()
    sleep(1)  # 等待页面加载完成
    
    # 获取页面截图
    screenshot = driver.execute_cdp_cmd("Page.captureScreenshot", {"format": "png", "fromSurface": True, "captureBeyondViewport": True})
    
    with open(working_image_path, 'wb') as f:
        img = base64.b64decode(screenshot['data'])
        f.write(img)

    # 关闭浏览器
    driver.quit()

# poster保存图片
def save_image(name_prefix, image, output_dir, index):
    # 生成标题加数字的文件名
    file_name = f"{name_prefix}_{index}.png"
    file_path = os.path.join(output_dir, file_name)
    
    # 保存图片
    image.save(file_path, "PNG")
    return file_path

# uploading part
def xhs_video_upload(video_path, your_title, your_desc, cookie_path):

    # 定义chrome属性
    prefs = {
        'profile.default_content_setting_values': {
            'notifications': 2  # 隐藏chromedriver的通知
        },
        'credentials_enable_service': False,  # 禁用凭据管理服务
        'profile.password_manager_enabled': False  # 隐藏chromedriver自带的保存密码功能
    }

    # 创建一个配置对象
    options = webdriver.ChromeOptions()
    options.add_experimental_option('prefs', prefs)
    options.add_experimental_option('excludeSwitches', ['enable-automation'])  # 设置为开发者模式,禁用chrome正受到自动化检测的显示
    options.add_argument('--disable-gpu')  # 谷歌文档提到需要加上这个属性来规避bug
    # 打开窗口
    worksite = webdriver.Chrome(options=options)

    # 最大化窗口
    worksite.maximize_window()
    worksite.implicitly_wait(5)

    # 小红书创作者中心
    url = "https://creator.xiaohongshu.com"
    worksite.get(url=url)
    # cooikes = worksite.get_cookies()
    # for cooike in cooikes:
    #     print(cooike)
    sleep(4)
    worksite.delete_all_cookies()

    # 持久化登录，之后登录就不需要上面的扫二维码
    login = CookieLogin(cookie_path)
    cookies = login.load_cookies()
    try:
        for cookie in cookies:
            cookie_dict = {
                'domain': '.xiaohongshu.com',
                'name': cookie.get('name'),
                'value': cookie.get('value'),
                "expires": '',
                'path': '/',
                'httpOnly': False,
                'HostOnly': False,
                'Secure': False
            }
            print(cookie_dict)
            worksite.add_cookie(cookie_dict)
    except Exception as e:
        print(e)

    sleep(5)
    
    worksite.refresh()

    # cooikes2 = worksite.get_cookies()
    # for cooike in cooikes2:
    #     print(cooike)

    sleep(5)
    url = "https://creator.xiaohongshu.com/publish/publish"
    worksite.get(url)

    sleep(2)
    # cooikes3 = worksite.get_cookies()
    # for cooike in cooikes2:
    #     print(cooike)

    video_upload = worksite.find_element(By.XPATH, '//*[@id="web"]/div/div/div[2]/div[1]/div/input')
    video_upload.send_keys(video_path)

    # 等待视频上传完成
    print("视频上传完成！")
    # 等待封面截取完成
    WebDriverWait(worksite, 120).until(EC.presence_of_element_located((By.XPATH, '//*[@id="publish-container"]/div[2]/div/div[2]/div[1]/div/div/div[1]/div[1]')))
     
    # 输入视频标题和描述---需要fullpath
    # title_input = worksite.find_element(By.XPATH, '//*[@id="el-id-1261-7"]')
    # /html/body/div[1]/div/div[2]/div/div[2]/main/div[3]/div/div/div[1]/div/div/div[2]/div/div[2]/div[2]/div[1]/div/input
    # //*[@id="el-id-2001-8"]
    title_input = worksite.find_element(By.CSS_SELECTOR, 'input[placeholder="填写标题，可能会有更多赞哦～"]')
    title_input.send_keys(your_title) 
    
    desc_input = worksite.find_element(By.XPATH, '//*[@id="post-textarea"]')
    desc_input.send_keys(your_desc)
    sleep(5)
    # 点击发布
    worksite.find_element(By.XPATH, '//*[@id="publish-container"]/div[2]/div/div[2]/div[7]/div/button[1]').click()
    print("视频发布成功！")
    sleep(10)
    worksite.close()
    worksite.quit()

def xhs_pic_upload(pic_paths, your_title, your_desc, cookie_path):

    # 定义chrome属性
    prefs = {
        'profile.default_content_setting_values': {
            'notifications': 2  # 隐藏chromedriver的通知
        },
        'credentials_enable_service': False,  # 禁用凭据管理服务
        'profile.password_manager_enabled': False  # 隐藏chromedriver自带的保存密码功能
    }

    # 创建一个配置对象
    options = webdriver.ChromeOptions()
    options.add_experimental_option('prefs', prefs)
    options.add_experimental_option('excludeSwitches', ['enable-automation'])  # 设置为开发者模式,禁用chrome正受到自动化检测的显示
    options.add_argument('--disable-gpu')  # 谷歌文档提到需要加上这个属性来规避bug
    # 打开窗口
    worksite = webdriver.Chrome(options=options)

    # 最大化窗口
    worksite.maximize_window()
    worksite.implicitly_wait(5)

    # 小红书创作者中心
    url = "https://creator.xiaohongshu.com"
    worksite.get(url=url)
    # cooikes = worksite.get_cookies()
    # for cooike in cooikes:
    #     print(cooike)
    sleep(4)
    worksite.delete_all_cookies()

    # 持久化登录，之后登录就不需要上面的扫二维码
    login = CookieLogin(cookie_path)
    cookies = login.load_cookies()
    try:
        for cookie in cookies:
            cookie_dict = {
                'domain': '.xiaohongshu.com',
                'name': cookie.get('name'),
                'value': cookie.get('value'),
                "expires": '',
                'path': '/',
                'httpOnly': False,
                'HostOnly': False,
                'Secure': False
            }
            print(cookie_dict)
            worksite.add_cookie(cookie_dict)
    except Exception as e:
        print(e)

    sleep(5)
    
    worksite.refresh()

    # cooikes2 = worksite.get_cookies()
    # for cooike in cooikes2:
    #     print(cooike)

    sleep(5)
    url = "https://creator.xiaohongshu.com/publish/publish"
    worksite.get(url)

    sleep(2)
    # cooikes3 = worksite.get_cookies()
    # for cooike in cooikes2:
    #     print(cooike)
    worksite.find_element(By.XPATH, '//*[@id="web"]/div/div/div/div[1]/div[2]/span').click()
 
    sleep(2)
    pic_upload = worksite.find_element(By.XPATH, '//*[@id="web"]/div/div/div/div[2]/div[1]/div/input')
    # //*[@id="web"]/div/div/div/div[2]/div[1]/div/div

    # print('\n'.join(pic_paths))
    pic_upload.send_keys('\n'.join(pic_paths))


    # 等待视频上传完成
    print("图片上传完成！")
    # 等待封面截取完成
    sign='//*[@id="web"]/div/div/div/div/div[1]/div[2]/div[1]/div/div[1]/div[1]/div/div/div[2]/div/div[1]/div[1]/div[1]/div/div[2]'
    WebDriverWait(worksite, 120).until(EC.presence_of_element_located((By.XPATH, sign)))
    # //*[@id="web"]/div/div/div/div/div/div[2]/div[1]/div/div[2]/div[2]/div/div[1]/div/div[9]/div[2]/div[2]/div[1]
    
    # 输入标题和描述--这两个和视频xpath一样
    title_input = worksite.find_element(By.CSS_SELECTOR, 'input[placeholder="填写标题会有更多赞哦～"]')
    # worksite.execute_script("arguments[0].value=arguments[1];", title_input, your_title)
    # worksite.execute_script("arguments[0].setAttribute('value', arguments[1]);", title_input, your_title)
    pyperclip.copy(your_title)
    title_input.send_keys(Keys.CONTROL, 'v')
    
    desc_input = worksite.find_element(By.XPATH, '//*[@id="post-textarea"]')
    # worksite.execute_script("arguments[0].innerText=arguments[1];", desc_input, your_desc)
    pyperclip.copy(your_desc)
    desc_input.send_keys(Keys.CONTROL, 'v')

    sleep(5)
    # 点击发布
    worksite.find_element(By.XPATH, '//*[@id="web"]/div/div/div/div/div[2]/div/button[1]').click()
    
    print("视频发布成功！")
    sleep(30)
    worksite.close()
    worksite.quit()

def dy_pic_upload(pic_paths, your_title, your_desc, cookie_path):
    # 定义chrome属性
    prefs = {
        'profile.default_content_setting_values': {
            'notifications': 2  # 隐藏chromedriver的通知
        },
        'credentials_enable_service': False,  # 禁用凭据管理服务
        'profile.password_manager_enabled': False  # 隐藏chromedriver自带的保存密码功能
    }

    # 创建一个配置对象
    options = webdriver.ChromeOptions()
    options.add_experimental_option('prefs', prefs)
    options.add_experimental_option('excludeSwitches', ['enable-automation'])  # 设置为开发者模式,禁用chrome正受到自动化检测的显示
    options.add_argument('--disable-gpu')  # 谷歌文档提到需要加上这个属性来规避bug
    # 打开窗口
    worksite = webdriver.Chrome(options=options)

    # 最大化窗口
    worksite.maximize_window()
    worksite.implicitly_wait(5)

    # 抖音创作者中心
    url = "https://creator.douyin.com"
    worksite.get(url=url)
    # cooikes = worksite.get_cookies()
    # for cooike in cooikes:
    #     print(cooike)
    sleep(4)
    worksite.delete_all_cookies()

    # 持久化登录，之后登录就不需要上面的扫二维码
    login = CookieLogin(cookie_path)
    cookies = login.load_cookies()
    try:
        for cookie in cookies:
            cookie_dict = {
                'domain': 'creator.douyin.com',
                'name': cookie.get('name'),
                'value': cookie.get('value'),
                "expires": '',
                'path': '/',
                'httpOnly': False,
                'HostOnly': False,
                'Secure': False
            }
            print(cookie_dict)
            worksite.add_cookie(cookie_dict)
    except Exception as e:
        print(e)

    sleep(5)
    
    worksite.refresh()

    # cooikes2 = worksite.get_cookies()
    # for cooike in cooikes2:
    #     print(cooike)

    sleep(5)
    url = "https://creator.douyin.com/creator-micro/content/upload"
    worksite.get(url)

    sleep(2)
    print("刷新成功")
    # cooikes3 = worksite.get_cookies()
    # for cooike in cooikes2:
    #     print(cooike)
    WebDriverWait(worksite, 120).until(EC.presence_of_element_located((By.XPATH, '//*[@id="root"]/div/div/div[2]/div[2]')))
    worksite.find_element(By.XPATH, '//*[@id="root"]/div/div/div[2]/div[2]').click()
    
    sleep(2)
    pic_upload = worksite.find_element(By.XPATH, '//*[@id="root"]/div/div/div[3]/div/div[2]/div/div/div[1]/input')
    print('\n'.join(pic_paths))
    pic_upload.send_keys('\n'.join(pic_paths))

    # 等待视频上传完成
    print("图片上传完成！")
    sleep(1)
    # worksite.switch_to.window(worksite.window_handles[0])
    sleep(5)
    # 等待检测完成
    sign='//*[@id="root"]/div/div/div/div[2]/div[2]/section/section/section/section[2]/div/section/p'
    WebDriverWait(worksite, 120).until(EC.presence_of_element_located((By.XPATH, sign)))

    # 输入标题和描述--这两个和视频xpath一样
    title_input = worksite.find_element(By.XPATH, '//*[@id="root"]/div/div/div/div[2]/div[1]/div/div[1]/div/div/div[2]/div/div/div/div[1]/div/input')
    pyperclip.copy(your_title)
    title_input.send_keys(Keys.CONTROL, 'v')
    
    desc_input = worksite.find_element(By.XPATH, '//*[@id="root"]/div/div/div/div[2]/div[1]/div/div[1]/div/div/div[2]/div/div/div/div[2]/div/div/div')
    pyperclip.copy(your_desc)
    desc_input.send_keys(Keys.CONTROL, 'v')
    
    # 选择音乐douyin独占
    worksite.find_element(By.XPATH, '//*[@id="root"]/div/div/div/div[2]/div[1]/div/div[4]/div[2]/div/div[2]/span').click()
    add_music_btn = WebDriverWait(worksite, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'audio-collection-container-WRbqgz')))
    actions = ActionChains(worksite)
    actions.move_to_element(add_music_btn).perform()
    sleep(5)
    music_span = worksite.find_element(By.XPATH, "//span[text()='使用']")
    music_btn = music_span.find_element(By.XPATH, "./..")
    actions.move_to_element(music_btn).click().perform()
    # art_desc = worksite.find_element(By.XPATH, '//*[@id="root"]/div/div/div/div[2]/div[1]/div/div[1]/div/div/div[1]/div')
    # actions.move_to_element(art_desc).click().perform()
    # 独占结束

    sleep(5)
    # 点击发布
    worksite.find_element(By.XPATH, '//*[@id="root"]/div/div/div/div[2]/div[1]/div/div[13]/button[1]').click()
    print("视频发布成功！")
    sleep(30)
    worksite.close()
    worksite.quit()

def archiving(target_dir, source_dir):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    # 获取源目录中的所有文件
    files = os.listdir(source_dir)
    png_files = []
    # 遍历每个文件并移动到目标目录
    for file in files:
        # 构建源文件和目标文件的完整路径
        source_file = os.path.join(source_dir, file)
        target_file = os.path.join(target_dir, file)
        shutil.move(source_file, target_file)
        if file.lower().endswith('.png'):
            png_files.append(target_file)
    print("归档完成！")
    return png_files

def main():
    # 输出目录
    pass


if __name__ == '__main__':
    main()
