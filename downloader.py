import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
import os
import sqlite3
from datetime import datetime
import urllib.parse
import logging 
import pyperclip  # URL 복사를 위한 라이브러리
import subprocess  # 파일 위치 열기를 위한 라이브러리

class DownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("파일 다운로더")
        self.root.geometry("1000x800")  # UI 크기 확대
        self.root.configure(bg='#f0f0f0')  # 배경색 추가
        
        # 메인 프레임 생성
        main_frame = tk.Frame(root, bg='#f0f0f0')
        main_frame.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)
        
        # DB 초기화
        self.init_db()
        
        # URL 입력 프레임
        url_frame = tk.Frame(main_frame, bg='#f0f0f0')
        url_frame.pack(fill=tk.X, pady=10)
        
        self.url_label = tk.Label(url_frame, text="다운로드 URL:", font=('Arial', 12), bg='#f0f0f0')
        self.url_label.pack(side=tk.LEFT, padx=5)
        
        self.url_entry = tk.Entry(url_frame, width=70, font=('Arial', 10))
        self.url_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        # 다운로드 버튼
        self.download_btn = tk.Button(url_frame, text="다운로드", command=self.start_download, 
                                      font=('Arial', 12), bg='#4CAF50', fg='white')
        self.download_btn.pack(side=tk.RIGHT, padx=5)
        
        # 진행 상태 프레임
        progress_frame = tk.Frame(main_frame, bg='#f0f0f0')
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.progress = ttk.Progressbar(progress_frame, length=500, mode='determinate')
        self.progress.pack(expand=True, fill=tk.X, padx=5)
        
        self.status_label = tk.Label(progress_frame, text="", font=('Arial', 10), bg='#f0f0f0')
        self.status_label.pack(pady=5)
        
        # 다운로드 히스토리 프레임
        history_frame = tk.Frame(main_frame, bg='#f0f0f0')
        history_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.history_label = tk.Label(history_frame, text="다운로드 기록:", font=('Arial', 12), bg='#f0f0f0')
        self.history_label.pack(anchor='w')
        
        # 트리뷰로 히스토리 표시 (리스트박스 대체)
        self.history_tree = ttk.Treeview(history_frame, 
            columns=('Date', 'Filename', 'Status', 'Actions'),
            show='headings',
            height=15)
        
        # 컬럼 설정
        self.history_tree.heading('Date', text='날짜')
        self.history_tree.heading('Filename', text='파일명')
        self.history_tree.heading('Status', text='상태')
        self.history_tree.heading('Actions', text='작업')
        
        # 컬럼 너비 설정
        self.history_tree.column('Date', width=150)
        self.history_tree.column('Filename', width=400)
        self.history_tree.column('Status', width=100)
        self.history_tree.column('Actions', width=150)
        
        # 스크롤바 설정
        history_scroll = ttk.Scrollbar(history_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=history_scroll.set)
        
        # 패킹
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        history_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 트리뷰 클릭 이벤트 바인딩
        self.history_tree.bind('<Button-1>', self.on_tree_click)
        
        self.load_history()
        
        # 로깅 설정 추가
        logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s: %(message)s',
            handlers=[
                logging.FileHandler('download.log'),  # 파일에 로그 저장
                logging.StreamHandler()  # 콘솔에도 로그 출력
            ]
        )
        

    def init_db(self):
        self.conn = sqlite3.connect('downloads.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute(''' 
            CREATE TABLE IF NOT EXISTS downloads
            (url TEXT, filename TEXT, download_date TEXT, status TEXT)
        ''')
        self.conn.commit()

    def detect_file_type(self, content):
        # 일반적인 파일 시그니처 매핑
        file_signatures = {
            b'\xFF\xD8\xFF': '.jpg',     # JPEG
            b'\x89PNG\r\n\x1a\n': '.png', # PNG
            b'PK\x03\x04': '.zip',        # ZIP
            b'Rar!\x1a\x07\x00': '.rar',  # RAR
            b'\x25PDF': '.pdf',           # PDF
            b'GIF87a': '.gif',            # GIF 87a
            b'GIF89a': '.gif',            # GIF 89a
            b'\xD0\xCF\x11\xE0': '.doc',  # DOC/XLS
        }
        
        for signature, ext in file_signatures.items():
            if content.startswith(signature):
                return ext
        
        return ''  # 알 수 없는 파일 유형

    def start_download(self):
        url = self.url_entry.get()
        if not url:
            messagebox.showerror("에러", "URL을 입력해주세요!")
            return
            
        try:
            # Yale Dataverse API 특별 처리
            if 'dataverse.yale.edu/api/access/dataset' in url:
                logging.info("Yale Dataverse API 데이터셋 감지")
                
                session = requests.Session()
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': '*/*'
                }
                
                # 스트리밍 없이 전체 응답을 한 번에 받기
                response = session.get(url, headers=headers, stream=False)
                response.raise_for_status()
                
                # 파일명 생성
                content_disposition = response.headers.get('content-disposition')
                if content_disposition and 'filename=' in content_disposition:
                    filename = content_disposition.split('filename=')[-1].strip('"')
                else:
                    filename = f'dataset_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
                
                # 다운로드 경로 선택
                save_path = filedialog.asksaveasfilename(
                    initialfile=filename,
                    defaultextension='.zip'
                )
                
                if not save_path:
                    logging.info("다운로드 취소됨")
                    return
                
                # 파일 저장
                logging.info(f"파일 저장 시작: {save_path}")
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                
                logging.info("다운로드 완료")
                self.status_label.config(text="다운로드 완료!")
                self.save_to_db(url, save_path, "완료")
                
                messagebox.showinfo("다운로드 완료", f"파일이 {save_path}에 저장되었습니다.")
                
            else:
                # 기존의 일반 다운로드 로직 유지
                logging.info("일반 다운로드 시작")
                response = requests.get(url, stream=True)
                response.raise_for_status()
                
                # 파일명 추출 및 저장 경로 설정 로직
                filename = self.get_filename_from_response(response, url)
                save_path = filedialog.asksaveasfilename(
                    initialfile=filename,
                    defaultextension=os.path.splitext(filename)[1]
                )
                
                if not save_path:
                    return
                
                # 파일 다운로드 및 저장
                self.download_file(response, save_path)
                self.save_to_db(url, save_path, "완료")

        except requests.exceptions.RequestException as e:
            error_msg = f"네트워크 오류: {str(e)}"
            logging.error(error_msg)
            messagebox.showerror("네트워크 에러", error_msg)
            self.save_to_db(url, filename, "실패")
        except Exception as e:
            error_msg = f"다운로드 오류: {str(e)}"
            logging.error(error_msg)
            messagebox.showerror("에러", error_msg)
            self.save_to_db(url, filename, "실패")

    def save_to_db(self, url, filename, status):
        download_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('''
            INSERT INTO downloads (url, filename, download_date, status)
            VALUES (?, ?, ?, ?)
        ''', (url, filename, download_date, status))
        self.conn.commit()
        self.load_history()

    def load_history(self):
        # 기존 항목 삭제
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # DB에서 데이터 로드
        self.cursor.execute('SELECT download_date, filename, status, url FROM downloads ORDER BY download_date DESC')
        for row in self.cursor.fetchall():
            download_date, filename, status, url = row
            self.history_tree.insert('', 'end', values=(
                download_date,    # 날짜
                filename,         # 파일명
                status,          # 상태
                "이동"           # 작업 버튼에서 '복사' 제거
            ))

    def on_tree_click(self, event):
        """트리뷰 클릭 이벤트 처리"""
        region = self.history_tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.history_tree.identify_column(event.x)
            item = self.history_tree.identify_row(event.y)
            
            if column == '#4':  # Actions 열
                values = self.history_tree.item(item)['values']
                
                if not values:
                    return
                    
                filename = values[1]  # 파일명
                
                # 클일 위치 열기
                if os.path.exists(filename):
                    self.open_file_location(filename)
                else:
                    messagebox.showwarning("경고", "파일을 찾을 수 없습니다.")

    def move_to_file_location(self):
        # 선택된 항목의 파일 위치 열기
        selected_item = self.download_tree.selection()
        if selected_item:
            item = self.download_tree.item(selected_item[0])
            values = item['values']
            if values:
                filename = values[0]
                file_path = os.path.join(self.download_folder, filename)
                self.open_file_location(file_path)

    def copy_selected_url(self):
        # 선택된 항목의 URL 복사
        selected_item = self.download_tree.selection()
        if selected_item:
            item = self.download_tree.item(selected_item[0])
            values = item['values']
            if values:
                url = values[1]
                self.copy_download_url(url)

    def open_file_location(self, file_path):
        """파일 위치 열기"""
        try:
            if os.path.exists(file_path):
                # 운영 체제별 파일 탐색기 열기
                if os.name == 'nt':  # Windows
                    subprocess.run(['explorer', '/select,', os.path.normpath(file_path)])
                elif sys.platform == 'darwin':  # macOS
                    subprocess.run(['open', '-R', file_path])
                else:  # Linux
                    subprocess.run(['xdg-open', os.path.dirname(file_path)])
            else:
                messagebox.showwarning("경고", "파일이 존재하지 않습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"파일 위치 열기 실패: {e}")

    def copy_download_url(self, url):
        """다운로드 URL 복사"""
        try:
            pyperclip.copy(url)
            messagebox.showinfo("알림", "URL이 클립보드에 복사되었습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"URL 복사 실패: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = DownloaderApp(root)
    root.mainloop() 