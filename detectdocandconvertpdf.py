import os
import time
import pythoncom
import win32com.client
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

DOC_FOLDER = os.path.abspath(r"words\docs")  # Convert to absolute path
PDF_FOLDER = os.path.abspath(r"words\pdfs")

if not os.path.exists(PDF_FOLDER):
    os.makedirs(PDF_FOLDER)

def wait_for_file(file_path, timeout=5):
    """Waits until the file is accessible (not being written by another process)."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            try:
                with open(file_path, "rb") as f:
                    f.read(10)  # Try reading the first few bytes
                return True
            except Exception:
                pass
        time.sleep(0.5)
    return False

def convert_doc_to_pdf(doc_path, pdf_path):
    """ Converts a Word document to PDF using Microsoft Word """
    pythoncom.CoInitialize()
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False

    try:
        doc = word.Documents.Open(doc_path)
        doc.SaveAs(pdf_path, FileFormat=17)  # 17 = PDF format
        doc.Close()
        print(f"Converted: {doc_path} -> {pdf_path}")
    except Exception as e:
        print(f"Error converting {doc_path}: {e}")
    finally:
        word.Quit()
        pythoncom.CoUninitialize()

class DocFileHandler(FileSystemEventHandler):
    """ Watches the folder for new .doc/.docx files and converts them """

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = os.path.abspath(event.src_path)
        if file_path.endswith((".doc", ".docx")):
            file_name = os.path.basename(file_path)
            pdf_path = os.path.join(PDF_FOLDER, file_name.rsplit(".", 1)[0] + ".pdf")

            print(f"New file detected: {file_name}")

            if wait_for_file(file_path):
                convert_doc_to_pdf(file_path, pdf_path)
            else:
                print(f"Skipped {file_name}: File was not ready in time.")

if __name__ == "__main__":
    observer = Observer()
    event_handler = DocFileHandler()
    
    observer.schedule(event_handler, DOC_FOLDER, recursive=False)
    observer.start()
    
    print(f"Monitoring {DOC_FOLDER} for new DOC/DOCX files...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()
