// API基础URL
const API_BASE_URL = 'http://localhost:8000';

// DOM元素
const elements = {
    // 标签页
    tabs: document.querySelectorAll('[data-tab]'),
    tabContents: document.querySelectorAll('.tab-content'),
    
    // 视频下载和上传
    youtubeUrl: document.getElementById('youtube-url'),
    resolution: document.getElementById('resolution'),
    downloadBtn: document.getElementById('download-btn'),
    videoUpload: document.getElementById('video-upload'),
    uploadBtn: document.getElementById('upload-btn'),
    videoPlayer: document.getElementById('video-preview'),
    videoContainer: document.getElementById('video-preview-container'),
    noVideoMessage: document.getElementById('no-video-message'),
    deleteVideoBtn: document.getElementById('delete-video-btn'),
    
    // 状态显示
    videoStatus: document.getElementById('video-status'),
    subtitleStatus: document.getElementById('subtitle-status'),
    dubbingStatus: document.getElementById('dubbing-status'),
    
    // 字幕生成
    generateSubtitlesBtn: document.getElementById('generate-subtitles-btn'),
    subtitleProgress: document.getElementById('subtitle-progress'),
    
    // 配音生成
    generateDubbingBtn: document.getElementById('generate-dubbing-btn'),
    dubbingProgress: document.getElementById('dubbing-progress'),
    
    // 系统设置
    apiKeyInput: document.getElementById('api-key'),
    targetLanguageInput: document.getElementById('target-language'),
    ttsMethodSelect: document.getElementById('tts-method'),
    saveSettingsBtn: document.getElementById('save-settings-btn'),
    
    // 通知
    toast: document.getElementById('toast')
};

// 初始化
async function init() {
    // 设置标签页切换
    elements.tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            elements.tabs.forEach(t => t.classList.remove('active'));
            elements.tabContents.forEach(c => c.classList.remove('active'));
            
            tab.classList.add('active');
            document.getElementById(tab.dataset.tab).classList.add('active');
        });
    });
    
    // 检查视频状态
    await checkVideoStatus();
    
    // 事件监听器
    setupEventListeners();
}

// 检查视频状态
async function checkVideoStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/video`);
        const data = await response.json();
        
        if (data.exists) {
            try {
                const filePath = encodeURIComponent(data.file);
                // 先检查文件是否存在
                const fileCheck = await fetch(`${API_BASE_URL}/video/file?path=${filePath}`);
                if (!fileCheck.ok) {
                    throw new Error('视频文件不存在');
                }
                
                elements.videoPlayer.src = `${API_BASE_URL}/video/file?path=${filePath}`;
                elements.videoPlayer.style.display = 'block';
                elements.noVideoMessage.style.display = 'none';
                elements.deleteVideoBtn.style.display = 'block';
                elements.videoStatus.textContent = '已加载';
                elements.videoStatus.className = 'text-success';
            } catch (fileError) {
                console.error('视频文件访问错误:', fileError);
                showToast('视频文件不可访问', 'danger');
                // 重置为无视频状态
                elements.videoPlayer.style.display = 'none';
                elements.noVideoMessage.style.display = 'flex';
                elements.deleteVideoBtn.style.display = 'none';
                elements.videoStatus.textContent = '文件丢失';
                elements.videoStatus.className = 'text-danger';
            }
        } else {
            elements.videoPlayer.style.display = 'none';
            elements.noVideoMessage.style.display = 'flex';
            elements.deleteVideoBtn.style.display = 'none';
            elements.videoStatus.textContent = '未加载';
            elements.videoStatus.className = 'text-muted';
        }
    } catch (error) {
        showToast('检查视频状态时出错，请确保后端服务已启动', 'danger');
        console.error('检查视频状态时出错:', error);
    }
}

// 显示通知
function showToast(message, type = 'success') {
    const toast = new bootstrap.Toast(elements.toast);
    const toastBody = elements.toast.querySelector('.toast-body');
    
    // 设置通知内容和样式
    toastBody.textContent = message;
    elements.toast.className = `toast align-items-center text-white bg-${type} border-0 position-fixed bottom-0 end-0 m-3`;
    
    // 显示通知
    toast.show();
    
    // 3秒后自动隐藏
    setTimeout(() => {
        toast.hide();
    }, 3000);
}

// 设置事件监听器
function setupEventListeners() {
    // 下载视频
    elements.downloadBtn.addEventListener('click', downloadVideo);
    
    // 上传视频
    elements.uploadBtn.addEventListener('click', () => elements.videoUpload.click());
    elements.videoUpload.addEventListener('change', uploadVideo);
    
    // 删除视频
    elements.deleteVideoBtn.addEventListener('click', deleteVideo);
    
    // 生成字幕
    elements.generateSubtitlesBtn.addEventListener('click', generateSubtitles);
    
    // 生成配音
    elements.generateDubbingBtn.addEventListener('click', generateDubbing);
    
    // 保存设置
    elements.saveSettingsBtn.addEventListener('click', saveSettings);
}

// 下载视频
async function downloadVideo() {
    const url = elements.youtubeUrl.value.trim();
    const resolution = elements.resolution.value;
    
    if (!url) {
        showToast('请输入YouTube视频链接', 'warning');
        return;
    }
    
    try {
        showToast('开始下载视频...', 'info');
        
        const response = await fetch(`${API_BASE_URL}/download`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: url,
                resolution: resolution
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('视频下载成功', 'success');
            await checkVideoStatus();
        } else {
            showToast(`下载失败: ${data.detail || '未知错误'}`, 'danger');
        }
    } catch (error) {
        showToast('下载视频时出错', 'danger');
        console.error('下载视频时出错:', error);
    }
}

// 上传视频
async function uploadVideo() {
    const file = elements.videoUpload.files[0];
    
    if (!file) {
        showToast('请选择要上传的文件', 'warning');
        return;
    }
    
    try {
        showToast('开始上传文件...', 'info');
        
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('文件上传成功', 'success');
            await checkVideoStatus();
        } else {
            showToast(`上传失败: ${data.detail || '未知错误'}`, 'danger');
        }
    } catch (error) {
        showToast('上传文件时出错', 'danger');
        console.error('上传文件时出错:', error);
    }
}

// 删除视频
async function deleteVideo() {
    try {
        const response = await fetch(`${API_BASE_URL}/video`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showToast('视频已删除', 'success');
            await checkVideoStatus();
        } else {
            showToast('删除视频失败', 'danger');
        }
    } catch (error) {
        showToast('删除视频时出错', 'danger');
        console.error('删除视频时出错:', error);
    }
}

// 生成字幕
async function generateSubtitles() {
    try {
        // 显示进度条
        elements.subtitleProgress.style.display = 'block';
        const progressBar = elements.subtitleProgress.querySelector('.progress-bar');
        progressBar.style.width = '0%';
        
        showToast('开始生成字幕...', 'info');
        
        const response = await fetch(`${API_BASE_URL}/process/text`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // 轮询任务状态
            await pollTaskStatus(data.task_id, 'subtitle');
            showToast('字幕生成完成', 'success');
        } else {
            showToast(`生成字幕失败: ${data.detail || '未知错误'}`, 'danger');
        }
    } catch (error) {
        showToast('生成字幕时出错', 'danger');
        console.error('生成字幕时出错:', error);
    } finally {
        elements.subtitleProgress.style.display = 'none';
    }
}

// 生成配音
async function generateDubbing() {
    try {
        // 显示进度条
        elements.dubbingProgress.style.display = 'block';
        const progressBar = elements.dubbingProgress.querySelector('.progress-bar');
        progressBar.style.width = '0%';
        
        showToast('开始生成配音...', 'info');
        
        const response = await fetch(`${API_BASE_URL}/process/audio`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // 轮询任务状态
            await pollTaskStatus(data.task_id, 'dubbing');
            showToast('配音生成完成', 'success');
        } else {
            showToast(`生成配音失败: ${data.detail || '未知错误'}`, 'danger');
        }
    } catch (error) {
        showToast('生成配音时出错', 'danger');
        console.error('生成配音时出错:', error);
    } finally {
        elements.dubbingProgress.style.display = 'none';
    }
}

// 轮询任务状态
async function pollTaskStatus(taskId, type) {
    const maxAttempts = 30;
    const interval = 2000;
    const progressBar = type === 'subtitle' 
        ? elements.subtitleProgress.querySelector('.progress-bar')
        : elements.dubbingProgress.querySelector('.progress-bar');
    
    for (let i = 0; i < maxAttempts; i++) {
        try {
            const response = await fetch(`${API_BASE_URL}/task/${taskId}`);
            const data = await response.json();
            
            if (data.status === 'completed') {
                progressBar.style.width = '100%';
                return true;
            } else if (data.status === 'failed') {
                throw new Error(data.error || '任务处理失败');
            }
            
            // 更新进度
            progressBar.style.width = `${data.progress}%`;
            progressBar.textContent = `${data.progress}% - ${data.message}`;
            
            // 等待下一次轮询
            await new Promise(resolve => setTimeout(resolve, interval));
        } catch (error) {
            console.error(`轮询${type}任务状态时出错:`, error);
            throw error;
        }
    }
    
    throw new Error('任务处理超时');
}

// 保存设置
async function saveSettings() {
    const apiKey = elements.apiKeyInput.value.trim();
    const targetLanguage = elements.targetLanguageInput.value.trim();
    const ttsMethod = elements.ttsMethodSelect.value;
    
    try {
        showToast('正在保存设置...', 'info');
        
        const response = await fetch(`${API_BASE_URL}/config`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                api_key: apiKey,
                target_language: targetLanguage,
                tts_method: ttsMethod
            })
        });
        
        if (response.ok) {
            showToast('设置保存成功', 'success');
        } else {
            const data = await response.json();
            showToast(`保存设置失败: ${data.detail || '未知错误'}`, 'danger');
        }
    } catch (error) {
        showToast('保存设置时出错', 'danger');
        console.error('保存设置时出错:', error);
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);