"""
Web dashboard for StreamHawk using Flask.
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import asdict

from flask import Flask, render_template, request, jsonify, send_from_directory

from .config import Config
from .extractor import StreamExtractor
from .downloader import YTDLPManager, DownloadProgress
from .imdb import IMDbClient
from .utils import extract_imdb_id, HistoryManager

app = Flask(__name__)

# Global state
config = Config()
history = HistoryManager() if config.save_history else None
active_downloads = {}


def get_download_dir():
    """Get download directory path."""
    return Path(config.download_dir)


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/extract', methods=['POST'])
def api_extract():
    """API endpoint to extract stream URL."""
    data = request.json
    imdb_input = data.get('imdb_id', '')
    
    imdb_id = extract_imdb_id(imdb_input)
    if not imdb_id:
        return jsonify({'error': 'Invalid IMDb ID'}), 400
    
    target_url = f"https://vidsrc.to/embed/movie/{imdb_id}"
    
    async def do_extract():
        extractor = StreamExtractor(config)
        stream_info, error = await extractor.extract(target_url)
        return stream_info, error
    
    try:
        stream_info, error = asyncio.run(do_extract())
        
        if error:
            return jsonify({'error': error}), 500
        
        if not stream_info:
            return jsonify({'error': 'Failed to extract stream'}), 500
        
        return jsonify({
            'imdb_id': imdb_id,
            'url': stream_info.url,
            'headers': stream_info.headers,
            'is_master': stream_info.is_master
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download', methods=['POST'])
def api_download():
    """API endpoint to start download."""
    data = request.json
    stream_url = data.get('url')
    headers = data.get('headers', {})
    filename = data.get('filename')
    quality = data.get('quality', config.default_quality)
    
    from .extractor import StreamInfo
    
    stream_info = StreamInfo(
        url=stream_url,
        headers=headers
    )
    
    download_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    async def do_download():
        downloader = YTDLPManager(config)
        
        def progress_callback(progress: DownloadProgress):
            active_downloads[download_id] = {
                'id': download_id,
                'percent': progress.percent,
                'speed': progress.speed,
                'eta': progress.eta,
                'status': progress.status
            }
        
        success = downloader.download(
            stream_info,
            output_name=filename,
            quality=quality,
            progress_callback=progress_callback
        )
        
        active_downloads[download_id]['status'] = 'complete' if success else 'error'
        return success
    
    # Start download in background
    asyncio.create_task(do_download())
    
    active_downloads[download_id] = {
        'id': download_id,
        'status': 'starting',
        'percent': 0
    }
    
    return jsonify({'download_id': download_id})


@app.route('/api/progress/<download_id>')
def api_progress(download_id):
    """Get download progress."""
    progress = active_downloads.get(download_id, {'status': 'unknown'})
    return jsonify(progress)


@app.route('/api/history')
def api_history():
    """Get download history."""
    if not history:
        return jsonify([])
    
    recent = history.get_recent(50)
    return jsonify(recent)


@app.route('/api/downloads')
def api_downloads():
    """List downloaded files."""
    download_dir = get_download_dir()
    files = []
    
    for ext in ['*.mp4', '*.mkv', '*.ts', '*.avi']:
        for file_path in download_dir.glob(ext):
            stat = file_path.stat()
            files.append({
                'name': file_path.name,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
    
    # Sort by modification time
    files.sort(key=lambda x: x['modified'], reverse=True)
    
    return jsonify(files)


@app.route('/api/metadata/<imdb_id>')
def api_metadata(imdb_id):
    """Fetch movie metadata."""
    async def do_fetch():
        client = IMDbClient()
        return await client.fetch_metadata(imdb_id)
    
    try:
        metadata = asyncio.run(do_fetch())
        if metadata:
            return jsonify(asdict(metadata))
        return jsonify({'error': 'Not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/downloads/<path:filename>')
def serve_download(filename):
    """Serve downloaded file."""
    return send_from_directory(get_download_dir(), filename)


# Simple HTML dashboard (embedded for standalone use)
DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StreamHawk Dashboard</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            text-align: center;
            padding: 40px 0;
            border-bottom: 1px solid #30363d;
            margin-bottom: 40px;
        }
        
        h1 {
            color: #58a6ff;
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #8b949e;
        }
        
        .card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }
        
        .card h2 {
            color: #58a6ff;
            margin-bottom: 20px;
            font-size: 1.3rem;
        }
        
        .form-group {
            margin-bottom: 16px;
        }
        
        label {
            display: block;
            margin-bottom: 6px;
            color: #8b949e;
            font-size: 0.9rem;
        }
        
        input[type="text"],
        select {
            width: 100%;
            padding: 10px 14px;
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
            color: #c9d1d9;
            font-size: 1rem;
        }
        
        input[type="text"]:focus,
        select:focus {
            outline: none;
            border-color: #58a6ff;
        }
        
        button {
            background: #238636;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 1rem;
            cursor: pointer;
            transition: background 0.2s;
        }
        
        button:hover {
            background: #2ea043;
        }
        
        button:disabled {
            background: #30363d;
            cursor: not-allowed;
        }
        
        .btn-secondary {
            background: #1f6feb;
        }
        
        .btn-secondary:hover {
            background: #388bfd;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #30363d;
            border-radius: 4px;
            overflow: hidden;
            margin: 16px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #238636, #2ea043);
            transition: width 0.3s;
        }
        
        .status {
            padding: 12px;
            border-radius: 6px;
            margin: 16px 0;
        }
        
        .status.success {
            background: rgba(46, 160, 67, 0.1);
            border: 1px solid #238636;
        }
        
        .status.error {
            background: rgba(248, 81, 73, 0.1);
            border: 1px solid #f85149;
        }
        
        .status.info {
            background: rgba(56, 139, 253, 0.1);
            border: 1px solid #1f6feb;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 24px;
        }
        
        .file-list {
            list-style: none;
        }
        
        .file-list li {
            padding: 12px;
            border-bottom: 1px solid #30363d;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .file-list li:last-child {
            border-bottom: none;
        }
        
        .file-name {
            color: #58a6ff;
            text-decoration: none;
        }
        
        .file-name:hover {
            text-decoration: underline;
        }
        
        .file-size {
            color: #8b949e;
            font-size: 0.9rem;
        }
        
        .hidden {
            display: none;
        }
        
        #streamInfo {
            background: #0d1117;
            padding: 16px;
            border-radius: 6px;
            margin: 16px 0;
            font-family: monospace;
            font-size: 0.9rem;
            word-break: break-all;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>StreamHawk</h1>
            <p class="subtitle">HLS Stream Extractor Dashboard</p>
        </header>
        
        <div class="grid">
            <div class="card">
                <h2>Extract & Download</h2>
                
                <div class="form-group">
                    <label for="imdbInput">IMDb ID or URL</label>
                    <input type="text" id="imdbInput" placeholder="tt0816692 or imdb.com/title/tt0816692">
                </div>
                
                <div class="form-group">
                    <label for="qualitySelect">Quality</label>
                    <select id="qualitySelect">
                        <option value="best">Best Available</option>
                        <option value="1080p">1080p</option>
                        <option value="720p">720p</option>
                        <option value="480p">480p</option>
                        <option value="360p">360p</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="filenameInput">Output Filename (optional)</label>
                    <input type="text" id="filenameInput" placeholder="movie.mp4">
                </div>
                
                <button id="extractBtn" onclick="startExtraction()">Extract Stream</button>
                <button id="downloadBtn" class="btn-secondary hidden" onclick="startDownload()">Start Download</button>
                
                <div id="status" class="status hidden"></div>
                
                <div id="streamInfo" class="hidden"></div>
                
                <div id="progressSection" class="hidden">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressBar" style="width: 0%"></div>
                    </div>
                    <div id="progressText">0%</div>
                </div>
            </div>
            
            <div class="card">
                <h2>Recent Downloads</h2>
                <ul class="file-list" id="fileList">
                    <li>Loading...</li>
                </ul>
            </div>
        </div>
        
        <div class="card">
            <h2>History</h2>
            <ul class="file-list" id="historyList">
                <li>Loading...</li>
            </ul>
        </div>
    </div>
    
    <script>
        let currentStream = null;
        let downloadId = null;
        
        function showStatus(message, type) {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = `status ${type}`;
            status.classList.remove('hidden');
        }
        
        function hideStatus() {
            document.getElementById('status').classList.add('hidden');
        }
        
        async function startExtraction() {
            const imdbInput = document.getElementById('imdbInput').value;
            if (!imdbInput) {
                showStatus('Please enter an IMDb ID or URL', 'error');
                return;
            }
            
            hideStatus();
            document.getElementById('extractBtn').disabled = true;
            showStatus('Extracting stream...', 'info');
            
            try {
                const response = await fetch('/api/extract', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({imdb_id: imdbInput})
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    currentStream = data;
                    showStatus('Stream extracted successfully!', 'success');
                    
                    document.getElementById('streamInfo').textContent = 
                        `URL: ${data.url.substring(0, 80)}...\nType: ${data.is_master ? 'Master playlist' : 'Media playlist'}`;
                    document.getElementById('streamInfo').classList.remove('hidden');
                    
                    document.getElementById('extractBtn').classList.add('hidden');
                    document.getElementById('downloadBtn').classList.remove('hidden');
                } else {
                    showStatus(data.error || 'Extraction failed', 'error');
                    document.getElementById('extractBtn').disabled = false;
                }
            } catch (err) {
                showStatus('Network error: ' + err.message, 'error');
                document.getElementById('extractBtn').disabled = false;
            }
        }
        
        async function startDownload() {
            if (!currentStream) return;
            
            const filename = document.getElementById('filenameInput').value;
            const quality = document.getElementById('qualitySelect').value;
            
            document.getElementById('downloadBtn').disabled = true;
            showStatus('Starting download...', 'info');
            
            try {
                const response = await fetch('/api/download', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        url: currentStream.url,
                        headers: currentStream.headers,
                        filename: filename,
                        quality: quality
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    downloadId = data.download_id;
                    document.getElementById('progressSection').classList.remove('hidden');
                    pollProgress();
                } else {
                    showStatus(data.error || 'Download failed', 'error');
                    document.getElementById('downloadBtn').disabled = false;
                }
            } catch (err) {
                showStatus('Network error: ' + err.message, 'error');
                document.getElementById('downloadBtn').disabled = false;
            }
        }
        
        async function pollProgress() {
            if (!downloadId) return;
            
            try {
                const response = await fetch(`/api/progress/${downloadId}`);
                const data = await response.json();
                
                const percent = data.percent || 0;
                document.getElementById('progressBar').style.width = percent + '%';
                document.getElementById('progressText').textContent = 
                    `${percent.toFixed(1)}% ${data.speed ? '(' + data.speed + ')' : ''}`;
                
                if (data.status === 'complete') {
                    showStatus('Download complete!', 'success');
                    loadDownloads();
                    resetForm();
                } else if (data.status === 'error') {
                    showStatus('Download failed', 'error');
                    resetForm();
                } else {
                    setTimeout(pollProgress, 1000);
                }
            } catch (err) {
                setTimeout(pollProgress, 2000);
            }
        }
        
        function resetForm() {
            currentStream = null;
            downloadId = null;
            document.getElementById('extractBtn').disabled = false;
            document.getElementById('extractBtn').classList.remove('hidden');
            document.getElementById('downloadBtn').classList.add('hidden');
            document.getElementById('downloadBtn').disabled = false;
            document.getElementById('streamInfo').classList.add('hidden');
            document.getElementById('progressSection').classList.add('hidden');
            document.getElementById('imdbInput').value = '';
        }
        
        async function loadDownloads() {
            try {
                const response = await fetch('/api/downloads');
                const files = await response.json();
                
                const list = document.getElementById('fileList');
                if (files.length === 0) {
                    list.innerHTML = '<li>No downloads yet</li>';
                } else {
                    list.innerHTML = files.map(f => `
                        <li>
                            <a href="/downloads/${encodeURIComponent(f.name)}" class="file-name" download>${f.name}</a>
                            <span class="file-size">${formatSize(f.size)}</span>
                        </li>
                    `).join('');
                }
            } catch (err) {
                console.error('Failed to load downloads:', err);
            }
        }
        
        async function loadHistory() {
            try {
                const response = await fetch('/api/history');
                const history = await response.json();
                
                const list = document.getElementById('historyList');
                if (history.length === 0) {
                    list.innerHTML = '<li>No history</li>';
                } else {
                    list.innerHTML = history.slice(0, 10).map(h => `
                        <li>
                            <span>${h.title}</span>
                            <span class="file-size">${h.status}</span>
                        </li>
                    `).join('');
                }
            } catch (err) {
                console.error('Failed to load history:', err);
            }
        }
        
        function formatSize(bytes) {
            const units = ['B', 'KB', 'MB', 'GB'];
            let unit = 0;
            while (bytes >= 1024 && unit < units.length - 1) {
                bytes /= 1024;
                unit++;
            }
            return bytes.toFixed(1) + ' ' + units[unit];
        }
        
        // Load on page load
        loadDownloads();
        loadHistory();
    </script>
</body>
</html>
'''


def run_web(host='0.0.0.0', port=8080, debug=False):
    """Run the web dashboard."""
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_web()
