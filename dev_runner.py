import time
import subprocess
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class CodeChangeHandler(FileSystemEventHandler):
    def __init__(self):
        self.process = None
        self.start_program()

    def start_program(self):
        if self.process:
            self.process.kill()
            time.sleep(1)  # 이전 프로세스가 완전히 종료되길 기다림
        
        print("\n=== 프로그램 (재)시작 ===")
        self.process = subprocess.Popen([sys.executable, 'downloader.py'])

    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            print(f"\n파일 변경 감지: {event.src_path}")
            self.start_program()

def start_development_mode():
    event_handler = CodeChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        if event_handler.process:
            event_handler.process.kill()
        observer.stop()
    observer.join()

if __name__ == "__main__":
    print("개발 모드 시작 - 파일 변경 감지중...")
    start_development_mode() 