import os
import sys
import shutil
import tempfile
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import zipfile
import io
import re
import subprocess
from pathlib import Path
import pandas as pd
import uuid  
import threading
# 设置路径
current_dir = os.path.dirname(os.path.abspath(__file__))
os.environ['PATH'] += os.pathsep + current_dir
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入核心模块
from core import *
from core.utils import *
from core.utils.onekeycleanup import cleanup
from core._1_ytdlp import download_video_ytdlp, find_video_files

# 常量定义
SUB_VIDEO = "output/output_sub.mp4"
DUB_VIDEO = "output/output_dub.mp4"
OUTPUT_DIR = "output"

# 创建 FastAPI 应用
app = FastAPI(
    title="VideoLingo API",
    description="API for VideoLingo video translation system",
    version="1.0.0"
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 模型定义
class DownloadRequest(BaseModel):
    url: str
    resolution: str = "1080"

class ConfigUpdate(BaseModel):
    key: str
    value: Any

class TranslationConfig(BaseModel):
    display_language: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    llm_support_json: Optional[bool] = None
    whisper_language: Optional[str] = None
    whisper_runtime: Optional[str] = None
    target_language: Optional[str] = None
    demucs: Optional[bool] = None
    burn_subtitles: Optional[bool] = None
    tts_method: Optional[str] = None

# 后台任务处理
background_tasks = {}

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


    try:
        background_tasks[task_id]["status"] = "processing"
        background_tasks[task_id]["progress"] = 0
        background_tasks[task_id]["message"] = "Using Whisper for transcription..."
        
        _2_asr.transcribe()
        background_tasks[task_id]["progress"] = 20
        background_tasks[task_id]["message"] = "Splitting long sentences..."
        
        _3_1_split_nlp.split_by_spacy()
        _3_2_split_meaning.split_sentences_by_meaning()
        background_tasks[task_id]["progress"] = 40
        background_tasks[task_id]["message"] = "Summarizing and translating..."
        
        _4_1_summarize.get_summary()
        if load_key("pause_before_translate"):
            # 在API模式下，我们不能暂停等待用户输入，所以直接继续
            pass
        _4_2_translate.translate_all()
        background_tasks[task_id]["progress"] = 60
        background_tasks[task_id]["message"] = "Processing and aligning subtitles..."
        
        _5_split_sub.split_for_sub_main()
        _6_gen_sub.align_timestamp_main()
        background_tasks[task_id]["progress"] = 80
        background_tasks[task_id]["message"] = "Merging subtitles to video..."
        
        _7_sub_into_vid.merge_subtitles_to_video()
        background_tasks[task_id]["progress"] = 100
        background_tasks[task_id]["message"] = "Subtitle processing complete! 🎉"
        background_tasks[task_id]["status"] = "completed"
    except Exception as e:
        background_tasks[task_id]["status"] = "failed"
        background_tasks[task_id]["error"] = str(e)

def process_audio_task(task_id: str):
    try:
        background_tasks[task_id]["status"] = "processing"
        background_tasks[task_id]["progress"] = 0
        background_tasks[task_id]["message"] = "Generate audio tasks"
        
        _8_1_audio_task.gen_audio_task_main()
        _8_2_dub_chunks.gen_dub_chunks()
        background_tasks[task_id]["progress"] = 25
        background_tasks[task_id]["message"] = "Extract refer audio"
        
        _9_refer_audio.extract_refer_audio_main()
        background_tasks[task_id]["progress"] = 50
        background_tasks[task_id]["message"] = "Generate all audio"
        
        _10_gen_audio.gen_audio()
        background_tasks[task_id]["progress"] = 75
        background_tasks[task_id]["message"] = "Merge full audio"
        
        _11_merge_audio.merge_full_audio()
        background_tasks[task_id]["progress"] = 90
        background_tasks[task_id]["message"] = "Merge dubbing to the video"
        
        _12_dub_to_vid.merge_video_audio()
        background_tasks[task_id]["progress"] = 100
        background_tasks[task_id]["message"] = "Audio processing complete! 🎇"
        background_tasks[task_id]["status"] = "completed"
    except Exception as e:
        background_tasks[task_id]["status"] = "failed"
        background_tasks[task_id]["error"] = str(e)

def create_zip_from_srt_files():
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for file_name in os.listdir(OUTPUT_DIR):
            if file_name.endswith(".srt"):
                file_path = os.path.join(OUTPUT_DIR, file_name)
                with open(file_path, "rb") as file:
                    zip_file.writestr(file_name, file.read())
    
    zip_buffer.seek(0)
    return zip_buffer

# API 路由
@app.get("/")
async def root():
    return {"message": "Welcome to VideoLingo API", "version": "1.0.0"}

@app.get("/config")
async def get_config():
    """获取当前配置"""
    config = {
        "display_language": load_key("display_language"),
        "api_key": load_key("api.key"),
        "base_url": load_key("api.base_url"),
        "model": load_key("api.model"),
        "llm_support_json": load_key("api.llm_support_json"),
        "whisper_language": load_key("whisper.language"),
        "whisper_runtime": load_key("whisper.runtime"),
        "target_language": load_key("target_language"),
        "demucs": load_key("demucs"),
        "burn_subtitles": load_key("burn_subtitles"),
        "tts_method": load_key("tts_method")
    }
    return config

@app.post("/config")
async def update_config(config: TranslationConfig):
    """更新配置"""
    updated = {}
    
    if config.display_language is not None:
        update_key("display_language", config.display_language)
        updated["display_language"] = config.display_language
        
    if config.api_key is not None:
        update_key("api.key", config.api_key)
        updated["api_key"] = config.api_key
        
    if config.base_url is not None:
        update_key("api.base_url", config.base_url)
        updated["base_url"] = config.base_url
        
    if config.model is not None:
        update_key("api.model", config.model)
        updated["model"] = config.model
        
    if config.llm_support_json is not None:
        update_key("api.llm_support_json", config.llm_support_json)
        updated["llm_support_json"] = config.llm_support_json
        
    if config.whisper_language is not None:
        update_key("whisper.language", config.whisper_language)
        updated["whisper_language"] = config.whisper_language
        
    if config.whisper_runtime is not None:
        update_key("whisper.runtime", config.whisper_runtime)
        updated["whisper_runtime"] = config.whisper_runtime
        
    if config.target_language is not None:
        update_key("target_language", config.target_language)
        updated["target_language"] = config.target_language
        
    if config.demucs is not None:
        update_key("demucs", config.demucs)
        updated["demucs"] = config.demucs
        
    if config.burn_subtitles is not None:
        update_key("burn_subtitles", config.burn_subtitles)
        updated["burn_subtitles"] = config.burn_subtitles
        
    if config.tts_method is not None:
        update_key("tts_method", config.tts_method)
        updated["tts_method"] = config.tts_method
    
    return {"message": "Configuration updated", "updated": updated}

@app.post("/config/{key}")
async def update_config_item(key: str, config: ConfigUpdate):
    """更新单个配置项"""
    update_key(key, config.value)
    return {"message": f"Configuration item {key} updated", "value": config.value}

@app.post("/download")
async def download_video(request: DownloadRequest):
    """从YouTube下载视频"""
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    try:
        download_video_ytdlp(request.url, resolution=request.resolution)
        video_file = find_video_files()
        return {"message": "Video downloaded successfully", "file": video_file}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download video: {str(e)}")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传视频或音频文件"""
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    raw_name = file.filename.replace(' ', '_')
    name, ext = os.path.splitext(raw_name)
    clean_name = re.sub(r'[^\w\-_\.]', '', name) + ext.lower()
    output_path = os.path.join(OUTPUT_DIR, clean_name)
    
    try:
        with open(output_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        if ext.lower() in load_key("allowed_audio_formats"):
            output_path = convert_audio_to_video(output_path)
            
        return {"message": "File uploaded successfully", "file": output_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

@app.delete("/video")
async def delete_video():
    """删除当前视频"""
    try:
        video_file = find_video_files()
        os.remove(video_file)
        if os.path.exists(OUTPUT_DIR):
            shutil.rmtree(OUTPUT_DIR)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        return {"message": "Video deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete video: {str(e)}")

@app.get("/video")
async def get_video():
    """获取当前视频信息"""
    try:
        video_file = find_video_files()
        return {"exists": True, "file": video_file}
    except:
        return {"exists": False}

# 全局任务字典（放在文件顶部）
background_tasks = {}

@app.post("/process/text")
async def start_text_processing(background_tasks_manager: BackgroundTasks):
    """开始文本处理（字幕生成）"""
    import uuid
    task_id = str(uuid.uuid4())
    background_tasks_manager.add_task(process_text_task, task_id)
    
    # 使用全局的background_tasks字典
    background_tasks[task_id] = {
        "id": task_id,
        "type": "text_processing",
        "status": "queued",
        "progress": 0,
        "message": "Task queued"
    }
    
    return {"task_id": task_id, "message": "Text processing started"}

@app.post("/process/audio")
async def start_audio_processing(background_tasks: BackgroundTasks):
    """开始音频处理（配音生成）"""
    import uuid
    task_id = str(uuid.uuid4())
    background_tasks.add_task(process_audio_task, task_id)
    
    background_tasks[task_id] = {
        "id": task_id,
        "type": "audio_processing",
        "status": "queued",
        "progress": 0,
        "message": "Task queued"
    }
    
    return {"task_id": task_id, "message": "Audio processing started"}

@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in background_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return background_tasks[task_id]

@app.get("/subtitles")
async def get_subtitles():
    """获取字幕视频信息"""
    if os.path.exists(SUB_VIDEO):
        return {"exists": True, "file": SUB_VIDEO}
    return {"exists": False}

@app.get("/dubbing")
async def get_dubbing():
    """获取配音视频信息"""
    if os.path.exists(DUB_VIDEO):
        return {"exists": True, "file": DUB_VIDEO}
    return {"exists": False}

@app.get("/download/subtitles")
async def download_subtitles():
    """下载所有SRT字幕文件"""
    zip_buffer = create_zip_from_srt_files()
    return FileResponse(
        zip_buffer, 
        media_type="application/zip",
        filename="subtitles.zip"
    )

@app.delete("/dubbing")
async def delete_dubbing_files():
    """删除配音文件"""
    if os.path.exists(DUB_VIDEO):
        os.remove(DUB_VIDEO)
    return {"message": "Dubbing files deleted successfully"}

@app.post("/archive")
async def archive_to_history():
    """归档到历史记录"""
    cleanup()
    return {"message": "Files archived to history successfully"}

@app.get("/video/output_sub")
async def get_subtitle_video():
    """获取带字幕的视频文件"""
    if not os.path.exists(SUB_VIDEO):
        raise HTTPException(status_code=404, detail="Subtitle video not found")
    return FileResponse(SUB_VIDEO)

@app.get("/video/output_dub")
async def get_dubbing_video():
    """获取带配音的视频文件"""
    if not os.path.exists(DUB_VIDEO):
        raise HTTPException(status_code=404, detail="Dubbing video not found")
    return FileResponse(DUB_VIDEO)

# 批处理相关的模型定义
class BatchVideoTask(BaseModel):
    video_file: str
    source_language: Optional[str] = None
    target_language: Optional[str] = None
    dubbing: Optional[bool] = False

class BatchUploadRequest(BaseModel):
    videos: List[str]  # 只接收视频文件列表
    source_language: Optional[str] = None  # 统一的源语言
    target_language: Optional[str] = None  # 统一的目标语言
    dubbing: Optional[bool] = False      # 统一的配音设置
# 批处理相关的模型定义
class BatchResponse(BaseModel):
    task_id: str
    status: str
    message: str
    progress: int = 0
    error: Optional[str] = None

@app.post("/batch/upload")
async def batch_upload_videos(request: BatchUploadRequest):
    """批量上传视频并更新任务配置"""
    try:
        # 确保输出目录存在
        os.makedirs("batch/input", exist_ok=True)
        
        # 读取或创建Excel文件
        excel_path = "batch/tasks_setting.xlsx"
        if os.path.exists(excel_path):
            df = pd.read_excel(excel_path)
        else:
            df = pd.DataFrame(columns=["Video File", "Source Language", "Target Language", "Dubbing","Status"])
        
        # 处理每个视频文件
        for video_file in request.videos:
            # 如果是URL，直接添加到Excel
            if video_file.startswith(('http://', 'https://')):
                video_path = video_file
            else:
                # 如果是本地文件，需要先保存到input目录
                video_name = os.path.basename(video_file)
                video_path = video_name
            
            # 添加到DataFrame，使用统一的设置
            new_row = {
                "Video File": video_path,
                "Source Language": request.source_language if request.source_language else "",
                "Target Language": request.target_language if request.target_language else "",
                "Dubbing": 1 if request.dubbing else 0
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        
        # 保存Excel文件
        df.to_excel(excel_path, index=False)
        
        return {"message": "Successfully updated batch tasks", "task_count": len(request.videos)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batch/task", response_model=BatchResponse)
async def create_batch_task():
    """创建批处理任务"""
    task_id = str(uuid.uuid4())
    background_tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "message": "Task initialized",
        "error": None
    }
    
    # 启动后台任务
    threading.Thread(target=process_batch_task, args=(task_id,)).start()
    
    return BatchResponse(
        task_id=task_id,
        status="pending",
        message="Task created",
        progress=0
    )

def process_batch_task(task_id: str):
    """处理批处理任务的后台函数"""
    try:
        background_tasks[task_id]["status"] = "processing"
        background_tasks[task_id]["progress"] = 0
        background_tasks[task_id]["message"] = "Reading task settings..."
        
        # 读取Excel配置文件
        import pandas as pd
        tasks_df = pd.read_excel('batch/tasks_setting.xlsx')
        total_tasks = len(tasks_df)
        
        for index, task in tasks_df.iterrows():
            try:
                # 更新进度
                progress = int((index + 1) / total_tasks * 100)
                background_tasks[task_id]["progress"] = progress
                background_tasks[task_id]["message"] = f"Processing task {index + 1}/{total_tasks}"
                
                # 设置语言配置
                if not pd.isna(task.get('source_language')):
                    update_key('whisper.language', task['source_language'])
                if not pd.isna(task.get('target_language')):
                    update_key('target_language', task['target_language'])
                
                # 处理视频
                video_file = task['video_file']
                dubbing = bool(task.get('dubbing', False))
                
                status, error_step, error_message = process_video(
                    video_file, 
                    dubbing=dubbing
                )
                
                if not status:
                    background_tasks[task_id]["message"] = f"Task {index + 1} failed: {error_message}"
                    continue
                    
            except Exception as e:
                background_tasks[task_id]["message"] = f"Task {index + 1} failed: {str(e)}"
                continue
                
        background_tasks[task_id]["status"] = "completed"
        background_tasks[task_id]["progress"] = 100
        background_tasks[task_id]["message"] = "All tasks completed"
            
    except Exception as e:
        background_tasks[task_id]["status"] = "failed"
        background_tasks[task_id]["error"] = str(e)
        background_tasks[task_id]["message"] = f"Task failed: {str(e)}"

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)