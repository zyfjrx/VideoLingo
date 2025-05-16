# ------------------------------------------
# 路径管理类
# ------------------------------------------
class PathManager:
    _instance = None
    _video_id = ""
    
    def __init__(self):
        raise RuntimeError('请使用 initialize() 方法初始化')
        
    @classmethod
    def initialize(cls, video_id: str = ""):
        if not cls._instance:
            cls._instance = super(PathManager, cls).__new__(cls)
            cls._video_id = video_id
        return cls._instance
    
    @classmethod
    def get_video_id(cls):
        return cls._video_id
    
    @classmethod
    def set_video_id(cls, video_id: str):
        cls._video_id = video_id
    
    @classmethod
    def get_video_path(cls):
        """获取带视频ID的路径前缀"""
        return f"output/{cls._video_id}" if cls._video_id else "output"

# ------------------------------------------
# 定义中间产出文件
# ------------------------------------------
def _2_CLEANED_CHUNKS():
    return f"{PathManager.get_video_path()}/log/cleaned_chunks.xlsx"

def _3_1_SPLIT_BY_NLP():
    return f"{PathManager.get_video_path()}/log/split_by_nlp.txt"

def _3_2_SPLIT_BY_MEANING():
    return f"{PathManager.get_video_path()}/log/split_by_meaning.txt"

def _4_1_TERMINOLOGY():
    return f"{PathManager.get_video_path()}/log/terminology.json"

def _4_2_TRANSLATION():
    return f"{PathManager.get_video_path()}/log/translation_results.xlsx"

def _5_SPLIT_SUB():
    return f"{PathManager.get_video_path()}/log/translation_results_for_subtitles.xlsx"

def _5_REMERGED():
    return f"{PathManager.get_video_path()}/log/translation_results_remerged.xlsx"

def _8_1_AUDIO_TASK():
    return f"{PathManager.get_video_path()}/audio/tts_tasks.xlsx"

# ------------------------------------------
# 定义音频文件
# ------------------------------------------
def _OUTPUT_DIR():
    return PathManager.get_video_path()

def _AUDIO_DIR():
    return f"{PathManager.get_video_path()}/audio"

def _RAW_AUDIO_FILE():
    return f"{PathManager.get_video_path()}/audio/raw.mp3"

def _VOCAL_AUDIO_FILE():
    return f"{PathManager.get_video_path()}/audio/vocal.mp3"

def _BACKGROUND_AUDIO_FILE():
    return f"{PathManager.get_video_path()}/audio/background.mp3"

def _AUDIO_REFERS_DIR():
    return f"{PathManager.get_video_path()}/audio/refers"

def _AUDIO_SEGS_DIR():
    return f"{PathManager.get_video_path()}/audio/segs"

def _AUDIO_TMP_DIR():
    return f"{PathManager.get_video_path()}/audio/tmp"

# ------------------------------------------
# 导出
# ------------------------------------------

__all__ = [
    "PathManager",
    "_2_CLEANED_CHUNKS",
    "_3_1_SPLIT_BY_NLP",
    "_3_2_SPLIT_BY_MEANING",
    "_4_1_TERMINOLOGY",
    "_4_2_TRANSLATION",
    "_5_SPLIT_SUB",
    "_5_REMERGED",
    "_8_1_AUDIO_TASK",
    "_OUTPUT_DIR",
    "_AUDIO_DIR",
    "_RAW_AUDIO_FILE",
    "_VOCAL_AUDIO_FILE",
    "_BACKGROUND_AUDIO_FILE",
    "_AUDIO_REFERS_DIR",
    "_AUDIO_SEGS_DIR",
    "_AUDIO_TMP_DIR"
]