import os
import json
import gradio as gr
from dotenv import load_dotenv
from postist_core import (
    fetch_task, 
    fetch_news, 
    reading_kb,
    generating, 
    shorten_topic, 
    writing_xhs_title, 
    writing_xhs_desc, 
    choosing_picture_template, 
    create_post, 
    creating_post,
    save_image, 
    split_text, 
    splitting_text,
    xhs_pic_upload,
    dy_pic_upload,
    archiving
)

def sequential_func(ab_number):
    # 输出目录
    current_dir = os.getcwd()
    working_dir = os.path.join(current_dir, "./tmp/")
    if not os.path.exists(working_dir):
        os.makedirs(working_dir)
    bg_dir = "./images/"
    font_dir = "./fonts/"
    cookie_dir = "./cookies/"
    prompt_dir = "./prompt/"
     
    # 获取今日任务
    task_number = ab_number[0]
    pic_title,pic_subtitles,pic_bodies,names,title,desc,archive_dir,acct_info = fetch_task(task_number)
    
    # 获取今日新闻
    if task_number in  ['4']:
        todaytopics, todaycontents = fetch_news(task_number)
        # 遍历新闻主题列表
        for todaytopic in todaytopics:
            # 存内容
            pic_subtitles.append(shorten_topic(todaytopic, prompt_dir+'shorten_topic.prompt'))
            pic_bodies.append(generating(todaytopic, prompt_dir+'generating.prompt'))
    elif task_number in ['6']:
        todaytopics, todaycontents = fetch_news(task_number)
        # 遍历新闻主题列表
        for todaytopic in todaytopics:
            pic_subtitles.append(shorten_topic(todaytopic, prompt_dir+'shorten_topic.prompt'))
        # 存内容   
        pic_bodies = todaycontents
    elif task_number in ['1', '2', '3']:
        pic_title, pic_subtitles, pic_bodies = reading_kb('./taskkb/immi/')
    elif task_number in ['5']:
        pic_title, pic_subtitles, pic_bodies = reading_kb('./taskkb/reading/')
    print('任务分配完成')
    # 生成内容
    title = writing_xhs_title(pic_bodies, prompt_dir+'xhs_title.prompt')
    desc = writing_xhs_desc(pic_bodies, prompt_dir+'xhs_desc.prompt')
    
    # 生成json文件
    # 创建一个包含所有变量的字典
    task_data = {
        "temp": task_number,
        "pic_title": pic_title,
        "pic_subtitles": pic_subtitles,
        "pic_bodies": pic_bodies,
        "names": names,
        "title": title,
        "desc": desc
    }
    # 将todaytopic和content写入json文件
    json_file_name = f"{pic_title}.json"
    json_file_path = os.path.join(working_dir, json_file_name)
    with open(json_file_path, 'w', encoding='utf-8') as file:
        json.dump(task_data, file, ensure_ascii=False, indent=4)   
    
    # 选择模板
    temp_data, word_number, line_number = choosing_picture_template(task_number, bg_dir, font_dir)

    # 循环subtitle
    if task_number in  ['5']:
        for pic_subtitle, pic_body in zip(pic_subtitles, pic_bodies):
            # 拆分文本
            segments = splitting_text(pic_body)
            # 创建并保存图片
            for i in range(0, len(segments), line_number):
                image = create_post(pic_title, pic_subtitle, '\n'.join(segments[i:i+line_number]), *temp_data)
                save_image(pic_subtitle.rstrip(), image, working_dir, i//line_number+1)
                print(f"Saved image {i//line_number+1}")
                names.append(f"{working_dir}{pic_subtitle.rstrip()}_{i//line_number+1}.png")
    else:        
        for pic_subtitle, pic_body in zip(pic_subtitles, pic_bodies):
            creating_post(pic_title, pic_subtitle, pic_body, task_number, working_dir)
            print(f"Saved image {1}")
            names.append(f"{working_dir}{pic_subtitle.rstrip()}.png")

    # 存文件名names到json文件
    task_data["names"] = names
    with open(json_file_path, 'w', encoding='utf-8') as file:
        json.dump(task_data, file, ensure_ascii=False, indent=4)    
         
    # 上传小红书
    # 读json数据
    # with open(working_dir+pic_title+'.json', 'r', encoding='utf-8') as file:
    #     task_data = json.load(file)
    # task_number, pic_title, pic_subtitles, pic_bodies, names, title, desc = task_data.values()

    # 清理tmp目录归档
    names = archiving(archive_dir + pic_title +"/", working_dir) 
   
    return title+'\n\n'+desc, names
    
def main():

    load_dotenv()
    task_list = ["1留学", "2移民", "4历史上的今天", "5读书", "6Github"]
    # task_list = ["4历史上的今天", "6Github"] 
    with gr.Blocks(title = "追踪热点") as demo:
        gr.Markdown("小红书创作")
        with gr.Row():
            daily_task = gr.Dropdown(choices=task_list, label="请选择任务")
            start_btn = gr.Button(value="确定")
        
        with gr.Row():
            task_textbox = gr.Textbox(label="标题和描述")
            task_gallery = gr.Gallery(label="图片")
            start_btn.click(sequential_func, inputs=daily_task, outputs=[task_textbox, task_gallery])
            
    demo.launch(server_name='127.0.0.1', server_port=5002)
    # demo.launch(server_name='0.0.0.0', server_port=5002, auth=("admin", "123456")) 
if __name__ == "__main__":
    main()
