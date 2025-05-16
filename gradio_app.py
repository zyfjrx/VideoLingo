import os, sys
import gradio as gr
import pandas as pd
from pathlib import Path
import shutil
from time import sleep

# 设置路径
current_dir = os.path.dirname(os.path.abspath(__file__))
os.environ['PATH'] += os.pathsep + current_dir
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.st_utils.imports_and_utils import *
from core import *
from core._1_ytdlp import download_video_ytdlp, find_video_files
from core.utils import *
from translations.translations import translate as t

# 常量定义
SUB_VIDEO = "output/output_sub.mp4"
DUB_VIDEO = "output/output_dub.mp4"
OUTPUT_DIR = "output"

# 辅助函数
def convert_audio_to_video(audio_file: str) -> str:
    output_video = os.path.join(OUTPUT_DIR, 'black_screen.mp4')
    if not os.path.exists(output_video):
        print(f"🎵➡️🎬 Converting audio to video with FFmpeg ......")
        ffmpeg_cmd = ['ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=black:s=640x360', '-i', audio_file, '-shortest', '-c:v', 'libx264', '-c:a', 'aac', '-pix_fmt', 'yuv420p', output_video]
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True, encoding='utf-8')
        print(f"🎵➡️🎬 Converted <{audio_file}> to <{output_video}> with FFmpeg\n")
        # 删除音频文件
        os.remove(audio_file)
    return output_video

def process_text():
    with gr.Progress() as progress:
        progress(0, desc=t("Using Whisper for transcription..."))
        _2_asr.transcribe()
        progress(0.2, desc=t("Splitting long sentences..."))
        _3_1_split_nlp.split_by_spacy()
        _3_2_split_meaning.split_sentences_by_meaning()
        progress(0.4, desc=t("Summarizing and translating..."))
        _4_1_summarize.get_summary()
        if load_key("pause_before_translate"):
            input(t("⚠️ PAUSE_BEFORE_TRANSLATE. Go to `output/log/terminology.json` to edit terminology. Then press ENTER to continue..."))
        _4_2_translate.translate_all()
        progress(0.6, desc=t("Processing and aligning subtitles..."))
        _5_split_sub.split_for_sub_main()
        _6_gen_sub.align_timestamp_main()
        progress(0.8, desc=t("Merging subtitles to video..."))
        _7_sub_into_vid.merge_subtitles_to_video()
        progress(1.0, desc=t("Subtitle processing complete! 🎉"))
    
    return gr.update(visible=True), gr.update(visible=True), gr.update(visible=True)

def process_audio():
    with gr.Progress() as progress:
        progress(0, desc=t("Generate audio tasks"))
        _8_1_audio_task.gen_audio_task_main()
        _8_2_dub_chunks.gen_dub_chunks()
        progress(0.25, desc=t("Extract refer audio"))
        _9_refer_audio.extract_refer_audio_main()
        progress(0.5, desc=t("Generate all audio"))
        _10_gen_audio.gen_audio()
        progress(0.75, desc=t("Merge full audio"))
        _11_merge_audio.merge_full_audio()
        progress(0.9, desc=t("Merge dubbing to the video"))
        _12_dub_to_vid.merge_video_audio()
        progress(1.0, desc=t("Audio processing complete! 🎇"))
    
    return gr.update(visible=True), gr.update(visible=True), gr.update(visible=True)

def download_video(url, resolution):
    res_dict = {
        "360p": "360",
        "1080p": "1080",
        "Best": "best"
    }
    res = res_dict.get(resolution, "1080")
    download_video_ytdlp(url, resolution=res)
    video_file = find_video_files()
    return video_file, gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)

def upload_video(file):
    if file is None:
        return None, gr.update(visible=False), gr.update(visible=True), gr.update(visible=True)
    
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    raw_name = os.path.basename(file.name).replace(' ', '_')
    name, ext = os.path.splitext(raw_name)
    clean_name = re.sub(r'[^\w\-_\.]', '', name) + ext.lower()
    
    output_path = os.path.join(OUTPUT_DIR, clean_name)
    with open(output_path, "wb") as f:
        f.write(file)
    
    if ext.lower() in load_key("allowed_audio_formats"):
        output_path = convert_audio_to_video(output_path)
    
    return output_path, gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)

def delete_video():
    try:
        video_file = find_video_files()
        os.remove(video_file)
        if os.path.exists(OUTPUT_DIR):
            shutil.rmtree(OUTPUT_DIR)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    except:
        pass
    return None, gr.update(visible=False), gr.update(visible=True), gr.update(visible=True)

def delete_dubbing_files():
    if os.path.exists(DUB_VIDEO):
        os.remove(DUB_VIDEO)
    return None, gr.update(visible=False), gr.update(visible=True)

def cleanup_files():
    cleanup()
    return None, None, gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=True)

def download_subtitles():
    return download_subtitle_zip()

def check_video_exists():
    try:
        video_file = find_video_files()
        return video_file, gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)
    except:
        return None, gr.update(visible=False), gr.update(visible=True), gr.update(visible=True)

def check_sub_video_exists():
    if os.path.exists(SUB_VIDEO):
        return SUB_VIDEO, gr.update(visible=True), gr.update(visible=True)
    return None, gr.update(visible=False), gr.update(visible=False)

def check_dub_video_exists():
    if os.path.exists(DUB_VIDEO):
        return DUB_VIDEO, gr.update(visible=True), gr.update(visible=True)
    return None, gr.update(visible=False), gr.update(visible=False)

def create_ui():
    with gr.Blocks(title="VideoLingo", theme=gr.themes.Soft()) as app:
        gr.HTML(r"""
        <div style="text-align: center; margin-bottom: 1rem">
            <img src="file/docs/logo.png" style="height: 100px; margin: auto">
            <h1 style="margin-top: 0.5rem">VideoLingo</h1>
            <p style="font-size: 1.2rem; color: #808080;">
                Hello, welcome to VideoLingo. If you encounter any issues, feel free to get instant answers with our Free QA Agent <a href="https://share.fastgpt.in/chat/share?shareId=066w11n3r9aq6879r4z0v9rh" target="_blank">here</a>! You can also try out our SaaS website at <a href="https://videolingo.io" target="_blank">videolingo.io</a> for free!
            </p>
        </div>
        """)
        
        # 设置选项卡
        with gr.Tabs() as tabs:
            # 视频下载/上传选项卡
            with gr.TabItem(t("a. Download or Upload Video")):
                # 视频显示区域
                video_output = gr.Video(label=t("Video"), visible=False)
                delete_btn = gr.Button(t("Delete and Reselect"), visible=False)
                
                with gr.Row(visible=True) as download_row:
                    with gr.Column(scale=3):
                        url_input = gr.Textbox(label=t("Enter YouTube link:"))
                    with gr.Column(scale=1):
                        resolution = gr.Dropdown(
                            choices=["360p", "1080p", "Best"],
                            value="1080p",
                            label=t("Resolution")
                        )
                    download_btn = gr.Button(t("Download Video"))
                
                with gr.Row(visible=True) as upload_row:
                    upload_input = gr.File(
                        label=t("Or upload video"),
                        file_types=load_key("allowed_video_formats") + load_key("allowed_audio_formats")
                    )
            
            # 字幕处理选项卡
            with gr.TabItem(t("b. Translate and Generate Subtitles")):
                gr.HTML(f"""
                <div style="margin-bottom: 1rem">
                    <p style="font-size: 1.1rem">{t("This stage includes the following steps:")}</p>
                    <ol style="font-size: 1rem; margin-left: 1.5rem">
                        <li>{t("WhisperX word-level transcription")}</li>
                        <li>{t("Sentence segmentation using NLP and LLM")}</li>
                        <li>{t("Summarization and multi-step translation")}</li>
                        <li>{t("Cutting and aligning long subtitles")}</li>
                        <li>{t("Generating timeline and subtitles")}</li>
                        <li>{t("Merging subtitles into the video")}</li>
                    </ol>
                </div>
                """)
                
                sub_video_output = gr.Video(label=t("Video with Subtitles"), visible=False)
                
                with gr.Row():
                    start_sub_btn = gr.Button(t("Start Processing Subtitles"), variant="primary")
                    download_subs_btn = gr.Button(t("Download All Srt Files"), visible=False)
                    archive_sub_btn = gr.Button(t("Archive to 'history'"), visible=False)
            
            # 配音处理选项卡
            with gr.TabItem(t("c. Dubbing")):
                gr.HTML(f"""
                <div style="margin-bottom: 1rem">
                    <p style="font-size: 1.1rem">{t("This stage includes the following steps:")}</p>
                    <ol style="font-size: 1rem; margin-left: 1.5rem">
                        <li>{t("Generate audio tasks and chunks")}</li>
                        <li>{t("Extract reference audio")}</li>
                        <li>{t("Generate and merge audio files")}</li>
                        <li>{t("Merge final audio into video")}</li>
                    </ol>
                </div>
                """)
                
                dub_video_output = gr.Video(label=t("Video with Dubbing"), visible=False)
                
                with gr.Row():
                    start_dub_btn = gr.Button(t("Start Audio Processing"), variant="primary")
                    delete_dub_btn = gr.Button(t("Delete dubbing files"), visible=False)
                    archive_dub_btn = gr.Button(t("Archive to 'history'"), visible=False)
            
            # 设置选项卡
            with gr.TabItem(t("Settings")):
                page_setting()
        
        # 事件处理
        download_btn.click(
            fn=download_video,
            inputs=[url_input, resolution],
            outputs=[video_output, delete_btn, download_row, upload_row]
        )
        
        upload_input.upload(
            fn=upload_video,
            inputs=[upload_input],
            outputs=[video_output, delete_btn, download_row, upload_row]
        )
        
        delete_btn.click(
            fn=delete_video,
            inputs=[],
            outputs=[video_output, delete_btn, download_row, upload_row]
        )
        
        start_sub_btn.click(
            fn=process_text,
            inputs=[],
            outputs=[sub_video_output, download_subs_btn, archive_sub_btn]
        )
        
        download_subs_btn.click(
            fn=download_subtitles,
            inputs=[],
            outputs=[]
        )
        
        archive_sub_btn.click(
            fn=cleanup_files,
            inputs=[],
            outputs=[video_output, sub_video_output, delete_btn, download_subs_btn, download_row, upload_row]
        )
        
        start_dub_btn.click(
            fn=process_audio,
            inputs=[],
            outputs=[dub_video_output, delete_dub_btn, archive_dub_btn]
        )
        
        delete_dub_btn.click(
            fn=delete_dubbing_files,
            inputs=[],
            outputs=[dub_video_output, delete_dub_btn]
        )
        
        archive_dub_btn.click(
            fn=cleanup_files,
            inputs=[],
            outputs=[video_output, dub_video_output, delete_btn, delete_dub_btn, download_row, upload_row]
        )
        
        # 页面加载时检查视频状态
        app.load(
            fn=check_video_exists,
            inputs=[],
            outputs=[video_output, delete_btn, download_row, upload_row]
        )
        
        app.load(
            fn=check_sub_video_exists,
            inputs=[],
            outputs=[sub_video_output, download_subs_btn, archive_sub_btn]
        )
        
        app.load(
            fn=check_dub_video_exists,
            inputs=[],
            outputs=[dub_video_output, delete_dub_btn, archive_dub_btn]
        )
        
    return app

if __name__ == "__main__":
    app = create_ui()
    app.launch(server_name="0.0.0.0", server_port=7860, share=True)