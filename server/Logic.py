import io
import re
import logging
import numpy as np
import datetime
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
try:
    import easyocr
except ImportError:
    easyocr = None
import zipfile
try:
    from PIL import Image
except ImportError:
    Image = None
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import os
try:
    from docx import Document
except ImportError:
    Document = None
try:
    from mtcnn import MTCNN
except ImportError:
    MTCNN = None
try:
    import olefile
except ImportError:
    olefile = None
try:
    from openpyxl import load_workbook
except ImportError:
    load_workbook = None
try:
    from pptx import Presentation
except ImportError:
    Presentation = None
try:
    import win32com.client
except ImportError:
    win32com = None

# 로깅 레벨 설정 (환경변수로 제어)
DEBUG_MODE = os.getenv("PII_DEBUG", "false").lower() == "true"
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='[%(levelname)s] %(message)s'
)

# 허깅페이스 토큰 설정 (환경 변수에서 읽기)
HF_TOKEN = os.getenv("HF_TOKEN", None)

NER_MODEL_NAME = "soddokayo/klue-roberta-base-ner"
print(f"[INFO] NER 모델 로딩 중: {NER_MODEL_NAME}")

if HF_TOKEN:
    ner_tokenizer = AutoTokenizer.from_pretrained(NER_MODEL_NAME, token=HF_TOKEN)
    ner_model = AutoModelForTokenClassification.from_pretrained(NER_MODEL_NAME, token=HF_TOKEN)
    print("[INFO] ✓ 허깅페이스 토큰 인증 완료")
else:
    print("[WARN] HF_TOKEN 환경 변수 없음 - 공개 모델로 시도")
    ner_tokenizer = AutoTokenizer.from_pretrained(NER_MODEL_NAME)
    ner_model = AutoModelForTokenClassification.from_pretrained(NER_MODEL_NAME)

ner_pipeline = pipeline("ner", model=ner_model, tokenizer=ner_tokenizer, grouped_entities=True)
print("[INFO] ✓ NER 모델 로딩 완료")

try:
    reader = easyocr.Reader(['ko', 'en'], gpu=False)
    print("[INFO] EasyOCR 초기화 완료")
except Exception as e:
    print(f"[WARN] EasyOCR 초기화 실패: {e}")
    reader = None

detector = MTCNN()

# ==========================
# 검증 함수 (Luhn + 주민번호)
# ==========================
def validate_luhn(card_number: str) -> bool:
    """Luhn 알고리즘으로 카드번호 검증"""
    digits = [int(d) for d in re.sub(r"\D", "", card_number)]
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            t = d * 2
            checksum += t - 9 if t > 9 else t
        else:
            checksum += d
    return checksum % 10 == 0

def validate_ssn(ssn: str) -> bool:
    """주민등록번호 검증 (생년월일 + 체크섬)"""
    ssn = re.sub(r"\D", "", ssn)
    if len(ssn) != 13:
        return False
    yy = int(ssn[0:2])
    mm = int(ssn[2:4])
    dd = int(ssn[4:6])
    g = int(ssn[6])
    
    if g not in [1, 2, 3, 4, 5, 6, 7, 8]:
        return False
    
    full_year = (1900 + yy) if g in [1, 2, 5, 6] else (2000 + yy)
    
    try:
        datetime.date(full_year, mm, dd)
    except ValueError:
        return False
    
    if full_year >= 2020:
        return True
    
    weights = [2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5]
    s = sum(int(ssn[i]) * weights[i] for i in range(12))
    check = (11 - (s % 11)) % 10
    return check == int(ssn[-1])

# ==========================
# 파일 파싱
# ==========================
def parse_file(File_Bytes: bytes, File_Ext: str) -> tuple:
    """
    파일을 파싱하여 텍스트를 추출합니다.
    Returns: (text, is_pure_image)
    """
    File_Ext = File_Ext.lower()
    
    if File_Ext == "txt":
        try:
            return File_Bytes.decode("utf-8"), False
        except UnicodeDecodeError:
            return File_Bytes.decode("cp949"), False

    elif File_Ext == "docx":
        try:
            file_stream = io.BytesIO(File_Bytes)
            doc = Document(file_stream)
        except Exception:
            raise ValueError("[ERROR] DOCX 파싱 실패: Document 객체 생성 불가")
        try:
            # 단락 텍스트 추출
            if DEBUG_MODE:
                print(f"[DEBUG] DOCX 단락 개수: {len(doc.paragraphs)}")
            para_texts = [para.text for para in doc.paragraphs if para.text]
            text = "\n".join(para_texts)
            
            # 테이블 텍스트 추출
            if DEBUG_MODE:
                print(f"[DEBUG] DOCX 테이블 개수: {len(doc.tables)}")
            for table in doc.tables:
                for row in table.rows:
                    row_text = " ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
                    if row_text:
                        text += "\n" + row_text
            
            if DEBUG_MODE:
                print(f"[DEBUG] 추출된 텍스트 길이: {len(text)} 글자")
            if not text.strip():
                print("[INFO] 텍스트 없음 → OCR 실행")
                text = run_ocr_on_docx_images(File_Bytes)
                if not text.strip():
                    print("[WARN] OCR 텍스트 추출 실패, 빈 문자열 반환")
            return text, False
        except Exception as e:
            raise ValueError(f"[ERROR] DOCX 파싱 실패 (내용 추출 중 오류): {e}")

    elif File_Ext == "pdf":
        try:
            doc = fitz.open(stream=File_Bytes, filetype="pdf")
            if doc.is_encrypted:
                raise ValueError("[ERROR] PDF 파싱 실패: 암호로 보호된 PDF 문서입니다.")
            
            # 텍스트 추출 최적화 (리스트 컴프리헨션 대신 join 사용)
            text_parts = []
            for page in doc:
                page_text = page.get_text()
                if page_text:
                    text_parts.append(page_text.replace("\n", " "))
            text = " ".join(text_parts)
            
            if not any(char.isalnum() for char in text):
                print("[INFO] 텍스트 없음 → OCR 실행")
                text = run_ocr_on_pdf_images(File_Bytes)
                if not text.strip():
                    print("[WARN] OCR 텍스트 추출 실패, 빈 문자열 반환")
            return text, False
        except Exception as e:
            raise ValueError(f"[ERROR] PDF 파싱 실패: {e}")
    
    elif File_Ext == "hwp":
        # win32com으로 HWP → HWPX 변환 시도
        if win32com is not None:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".hwp") as tmp:
                    tmp.write(File_Bytes)
                    tmp_path = tmp.name
                tmp_hwpx_path = tmp_path + "x"
                try:
                    hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
                    hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
                    hwp.Open(tmp_path)
                    hwp.SaveAs(tmp_hwpx_path, "HWPX")
                    hwp.Quit()
                except Exception:
                    raise ValueError("[ERROR] HWP 변환 실패 또는 암호화")
                with open(tmp_hwpx_path, "rb") as f:
                    converted = f.read()
                os.remove(tmp_path)
                os.remove(tmp_hwpx_path)
                return parse_file(converted, "hwpx")
            except Exception as e:
                print(f"[WARN] HWP → HWPX 변환 실패, 기본 로직으로 진행: {e}")
        
        # 기본 HWP 파싱
        if olefile is None:
            raise ValueError("[ERROR] HWP 파싱 실패: olefile 라이브러리 미설치")
        try:
            ole = olefile.OleFileIO(io.BytesIO(File_Bytes))
            text = ""
            
            # 방법 1: PrvText 스트림에서 추출
            if ole.exists("PrvText"):
                stream = ole.openstream("PrvText")
                raw = stream.read()
                text = raw.decode("utf-16", errors="ignore").strip()
                if DEBUG_MODE:
                    print(f"[DEBUG] HWP PrvText 추출: {len(text)} 글자")
            
            # 방법 2: BodyText 섹션에서 추출 (더 정확함)
            if not text.strip():
                if DEBUG_MODE:
                    print("[DEBUG] PrvText 없음, BodyText 시도")
                for entry in ole.listdir():
                    if entry[0] == "BodyText":
                        try:
                            stream = ole.openstream(entry)
                            raw = stream.read()
                            decoded = raw.decode("utf-16", errors="ignore")
                            cleaned = ''.join(c for c in decoded if c.isprintable() or c in '\n\r\t ')
                            text += cleaned + "\n"
                        except Exception:
                            continue
                if DEBUG_MODE:
                    print(f"[DEBUG] HWP BodyText 추출: {len(text)} 글자")
            
            # 방법 3: OCR 시도
            if not text.strip():
                print("[INFO] HWP 텍스트 없음 → 이미지 OCR 시도")
                text = run_ocr_on_hwp_images(File_Bytes)
            
            ole.close()
            text = text.strip()
            
            # HWP 텍스트 정리
            text = re.sub(r'<>', ' ', text)
            text = re.sub(r'<', ' ', text)
            text = re.sub(r'>', ' ', text)
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            # 한글 띄어쓰기 정규화 ("이 무 송" -> "이무송")
            original_text = text
            while True:
                prev = text
                text = re.sub(r'([가-힣])\s+([가-힣])(?=\s|[가-힣]|$)', r'\1\2', text)
                if prev == text:
                    break
            
            if text != original_text and DEBUG_MODE:
                print(f"[INFO] ⚠ HWP 한글 띄어쓰기 정규화 적용")
                print(f"[DEBUG] 원본: {original_text[:200]}")
                print(f"[DEBUG] 정규화: {text[:200]}")
            
            print(f"[INFO] HWP 최종 텍스트: {len(text)} 글자")
            if DEBUG_MODE:
                print(f"[DEBUG] HWP 텍스트 미리보기: {text[:200]}")
            return text, False
        except Exception as e:
            raise ValueError(f"[ERROR] HWP 파싱 실패: {e}")
    
    elif File_Ext == "hwpx":
        try:
            if DEBUG_MODE:
                print("[INFO] HWPX 파일 파싱 시작")
            with zipfile.ZipFile(io.BytesIO(File_Bytes)) as z:
                # Contents/section*.xml 파일만 읽기 (최적화)
                # 불필요한 XML 파일 제외 (settings, styles 등)
                section_files = [n for n in z.namelist() 
                                if n.startswith('Contents/section') and n.endswith('.xml')
                                and not any(skip in n for skip in ['settings', 'styles', 'header', 'footer'])]
                if DEBUG_MODE:
                    print(f"[DEBUG] HWPX section 파일: {section_files}")
                
                if not section_files:
                    # section 파일이 없으면 Contents/ 내 XML만 시도
                    section_files = [n for n in z.namelist() 
                                    if n.startswith('Contents/') and n.endswith('.xml')
                                    and not any(skip in n for skip in ['settings', 'styles', 'header', 'footer'])]
                    if DEBUG_MODE:
                        print(f"[DEBUG] HWPX Contents XML 파일: {len(section_files)}개")
                
                if not section_files:
                    raise ValueError("[ERROR] HWPX 파싱 실패: XML 파일 없음 (암호화 또는 손상)")
                
                text = ""
                for name in section_files:
                    try:
                        data = z.read(name).decode("utf-8", errors="ignore")
                        cleaned = re.sub(r"<[^>]+>", " ", data)
                        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                        if cleaned:
                            text += cleaned + "\n"
                            if DEBUG_MODE:
                                print(f"[DEBUG] {name}: {len(cleaned)} 글자 추출")
                    except Exception as e:
                        if DEBUG_MODE:
                            print(f"[WARN] {name} 파싱 실패: {e}")
                        continue
                
                text = text.strip()
                if DEBUG_MODE:
                    print(f"[INFO] HWPX 텍스트 추출 완료: {len(text)} 글자")
                
                if not text:
                    if DEBUG_MODE:
                        print("[INFO] HWPX 텍스트 없음 → OCR 실행")
                    text = run_ocr_on_hwpx_images(File_Bytes)
                
                if text and DEBUG_MODE:
                    print(f"[DEBUG] HWPX 최종 텍스트 미리보기: {text[:200]}")
                return text, False
        except zipfile.BadZipFile:
            raise ValueError("[ERROR] HWPX 파싱 실패: 손상된 ZIP 파일")
        except Exception as e:
            raise ValueError(f"[ERROR] HWPX 파싱 실패: {e}")
    
    elif File_Ext in ["xls", "xlsx"]:
        if File_Ext == "xlsx":
            if load_workbook is None:
                raise ValueError("[ERROR] XLSX 파싱 실패: openpyxl 라이브러리 미설치")
            try:
                wb = load_workbook(io.BytesIO(File_Bytes), data_only=True)
                text = ""
                for sheet in wb.worksheets:
                    for row in sheet.iter_rows(values_only=True):
                        for cell in row:
                            if cell is not None:
                                cell_str = str(cell).strip()
                                if cell_str:
                                    text += cell_str + "\n"
                return text.strip(), False
            except Exception as e:
                raise ValueError(f"[ERROR] XLSX 파싱 실패: {e}")
        else:  # .xls
            if win32com is None:
                raise ValueError("[ERROR] XLS 파싱 실패: win32com 미설치")
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xls") as tmp:
                    tmp.write(File_Bytes)
                    tmp_path = tmp.name
                tmp_xlsx_path = tmp_path + "x"
                try:
                    excel = win32com.client.Dispatch("Excel.Application")
                    excel.Visible = False
                    wb = excel.Workbooks.Open(tmp_path)
                    wb.SaveAs(tmp_xlsx_path, FileFormat=51)
                    wb.Close(SaveChanges=False)
                    excel.Quit()
                except Exception:
                    raise ValueError("[ERROR] XLS → XLSX 변환 실패 또는 암호")
                with open(tmp_xlsx_path, "rb") as f:
                    converted = f.read()
                os.remove(tmp_path)
                os.remove(tmp_xlsx_path)
                return parse_file(converted, "xlsx")
            except Exception as e:
                raise ValueError(f"[ERROR] XLS 파싱 실패: {e}")
    
    elif File_Ext in ["ppt", "pptx"]:
        if File_Ext == "pptx":
            if Presentation is None:
                raise ValueError("[ERROR] PPTX 파싱 실패: python-pptx 라이브러리 미설치")
            try:
                prs = Presentation(io.BytesIO(File_Bytes))
                text = ""
                for slide in prs.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, "text"):
                            text += shape.text + "\n"
                ocr_text = run_ocr_on_pptx_images(File_Bytes)
                if ocr_text:
                    text += "\n" + ocr_text
                return text.strip(), False
            except Exception as e:
                raise ValueError(f"[ERROR] PPTX 파싱 실패: {e}")
        else:  # .ppt
            if win32com is None:
                raise ValueError("[ERROR] PPT 파싱 실패: win32com 미설치")
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".ppt") as tmp:
                    tmp.write(File_Bytes)
                    tmp_path = tmp.name
                tmp_pptx_path = tmp_path + "x"
                try:
                    pp = win32com.client.Dispatch("PowerPoint.Application")
                    pp.Visible = False
                    pres = pp.Presentations.Open(tmp_path, WithWindow=False)
                    pres.SaveAs(tmp_pptx_path, FileFormat=24)
                    pres.Close()
                    pp.Quit()
                except Exception:
                    raise ValueError("[ERROR] PPT → PPTX 변환 실패 또는 암호")
                with open(tmp_pptx_path, "rb") as f:
                    converted = f.read()
                os.remove(tmp_path)
                os.remove(tmp_pptx_path)
                return parse_file(converted, "pptx")
            except Exception as e:
                raise ValueError(f"[ERROR] PPT 파싱 실패: {e}")
    
    elif File_Ext == "doc":
        if win32com is None:
            raise ValueError("[ERROR] DOC 파싱 실패: win32com 미설치")
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".doc") as tmp:
                tmp.write(File_Bytes)
                tmp_path = tmp.name
            tmp_docx_path = tmp_path + "x"
            try:
                word = win32com.client.Dispatch("Word.Application")
                word.Visible = False
                doc = word.Documents.Open(tmp_path)
                doc.SaveAs(tmp_docx_path, FileFormat=16)
                doc.Close()
                word.Quit()
            except Exception:
                raise ValueError("[ERROR] DOC 변환/파싱 실패: 암호")
            with open(tmp_docx_path, "rb") as f:
                converted = f.read()
            os.remove(tmp_path)
            os.remove(tmp_docx_path)
            return parse_file(converted, "docx")
        except Exception as e:
            raise ValueError(f"[ERROR] DOC 파싱 실패: {e}")
    
    elif File_Ext in ["png", "jpg", "jpeg", "bmp", "webp", "gif", "tiff"]:
        print(f"[INFO] 이미지 파일 감지: {File_Ext}")
        ocr_text = run_ocr_on_single_image(File_Bytes)
        return ocr_text, True
    
    else:
        raise ValueError(f"[ERROR] 지원하지 않는 파일 형식: {File_Ext}")

# ==========================
# OCR
# ==========================
def run_ocr_on_single_image(image_bytes: bytes) -> str:
    """단일 이미지에서 OCR 수행"""
    if reader is None:
        print("[WARN] EasyOCR이 초기화되지 않았습니다.")
        return ""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        result = reader.readtext(np.array(img))
        ocr_text = "\n".join([box[1] for box in result])
        print(f"[INFO] 이미지 OCR 완료: {len(ocr_text)} 글자 추출")
        return ocr_text.strip()
    except Exception as e:
        print(f"[ERROR] 이미지 OCR 실패: {e}")
        return ""

def _process_docx_image(args):
    """단일 DOCX 이미지 OCR 처리 (병렬 처리용)"""
    image_name, img_bytes = args
    if reader is None:
        return ""
    try:
        image = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        result = reader.readtext(np.array(image), detail=1, paragraph=False)
        text = ""
        for box in result:
            if box[2] > 0.1:
                text += box[1] + "\n"
        if text:
            print(f"[INFO] ✓ {image_name} OCR 완료: {len(text)} 글자")
        return text
    except Exception as e:
        print(f"[ERROR] {image_name} OCR 실패: {e}")
        return ""

def run_ocr_on_docx_images(file_bytes):
    if reader is None:
        print("[WARN] EasyOCR이 초기화되지 않았습니다.")
        return ""
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as docx_zip:
            image_files = [f for f in docx_zip.namelist() if f.startswith("word/media/")]
            print(f"[INFO] DOCX 내부 이미지 {len(image_files)}개 발견, OCR 시작")
            
            if len(image_files) == 0:
                return ""
            
            # 이미지 1개면 순차 처리, 2개 이상이면 병렬 처리
            if len(image_files) == 1:
                with docx_zip.open(image_files[0]) as image_file:
                    return _process_docx_image((image_files[0], image_file.read()))
            
            # 병렬 처리
            image_tasks = []
            for image_name in image_files:
                with docx_zip.open(image_name) as image_file:
                    image_tasks.append((image_name, image_file.read()))
            
            ocr_text = ""
            max_workers = min(4, os.cpu_count() or 2)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(_process_docx_image, task) for task in image_tasks]
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        ocr_text += result
            return ocr_text.strip()
    except Exception as e:
        print(f"[ERROR] DOCX 이미지 OCR 실패: {e}")
        return ""

def run_ocr_on_pdf_images(pdf_bytes: bytes) -> str:
    ocr_text = ""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        print(f"[INFO] PDF {len(doc)}페이지 OCR 시작")
        for idx, page in enumerate(doc):
            pix = page.get_pixmap()
            img = Image.open(io.BytesIO(pix.tobytes("ppm")))
            try:
                result = reader.readtext(np.array(img))
                for box in result:
                    ocr_text += box[1] + "\n"
            except Exception as e:
                print(f"[ERROR] EasyOCR 실패 (페이지 {idx}): {e}")
    return ocr_text.strip()

def _process_hwp_image(args):
    """단일 HWP 이미지 OCR 처리 (병렬 처리용)"""
    entry_name, img_bytes = args
    if reader is None:
        return ""
    try:
        img = Image.open(io.BytesIO(img_bytes))
        result = reader.readtext(np.array(img))
        text = "".join([box[1] + "\n" for box in result])
        if text:
            print(f"[INFO] ✓ {entry_name} OCR 완료")
        return text
    except Exception:
        return ""

def run_ocr_on_hwp_images(hwp_bytes: bytes) -> str:
    """HWP 파일 내부 이미지에서 OCR 수행"""
    if reader is None or olefile is None:
        return ""
    try:
        ole = olefile.OleFileIO(io.BytesIO(hwp_bytes))
        image_tasks = []
        for entry in ole.listdir():
            if entry[0] == "BinData":
                try:
                    stream = ole.openstream(entry)
                    img_bytes = stream.read()
                    entry_name = "/".join(entry)
                    image_tasks.append((entry_name, img_bytes))
                except Exception:
                    continue
        ole.close()
        
        if len(image_tasks) == 0:
            return ""
        
        # 이미지 1개면 순차, 2개 이상이면 병렬
        if len(image_tasks) == 1:
            return _process_hwp_image(image_tasks[0])
        
        ocr_text = ""
        max_workers = min(4, os.cpu_count() or 2)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_process_hwp_image, task) for task in image_tasks]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    ocr_text += result
        
        if ocr_text:
            print(f"[INFO] HWP 이미지 OCR 완료: {len(ocr_text)} 글자 추출")
        return ocr_text.strip()
    except Exception as e:
        print(f"[ERROR] HWP 이미지 OCR 실패: {e}")
        return ""

def _process_pptx_image(args):
    """단일 PPTX 이미지 OCR 처리 (병렬 처리용)"""
    image_name, img_bytes = args
    if reader is None:
        return ""
    try:
        img = Image.open(io.BytesIO(img_bytes))
        result = reader.readtext(np.array(img))
        text = "".join([box[1] + "\n" for box in result])
        if text:
            print(f"[INFO] ✓ {image_name} OCR 완료")
        return text
    except Exception:
        return ""

def run_ocr_on_pptx_images(pptx_bytes: bytes) -> str:
    """PPTX 파일 내부 이미지에서 OCR 수행"""
    if reader is None:
        return ""
    try:
        with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as pptx_zip:
            image_files = [f for f in pptx_zip.namelist() if f.startswith("ppt/media/")]
            print(f"[INFO] PPTX 내부 이미지 {len(image_files)}개 발견, OCR 시작")
            
            if len(image_files) == 0:
                return ""
            
            # 이미지 1개면 순차, 2개 이상이면 병렬
            if len(image_files) == 1:
                with pptx_zip.open(image_files[0]) as image_file:
                    return _process_pptx_image((image_files[0], image_file.read()))
            
            image_tasks = []
            for image_name in image_files:
                with pptx_zip.open(image_name) as image_file:
                    image_tasks.append((image_name, image_file.read()))
            
            ocr_text = ""
            max_workers = min(4, os.cpu_count() or 2)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(_process_pptx_image, task) for task in image_tasks]
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        ocr_text += result
            
            if ocr_text:
                print(f"[INFO] PPTX 이미지 OCR 완료: {len(ocr_text)} 글자 추출")
            return ocr_text.strip()
    except Exception as e:
        print(f"[ERROR] PPTX 이미지 OCR 실패: {e}")
        return ""

def run_ocr_on_hwpx_images(hwpx_bytes: bytes) -> str:
    """HWPX 파일 내부 이미지에서 OCR 수행"""
    if reader is None:
        return ""
    ocr_text = ""
    try:
        with zipfile.ZipFile(io.BytesIO(hwpx_bytes)) as z:
            for name in z.namelist():
                if name.startswith("Contents/") and name.lower().endswith((".jpg", ".png", ".bmp")):
                    img = Image.open(io.BytesIO(z.read(name)))
                    result = reader.readtext(np.array(img))
                    for box in result:
                        ocr_text += box[1] + "\n"
    except Exception as e:
        print(f"[ERROR] HWPX 이미지 OCR 실패: {e}")
    return ocr_text.strip()

# ==========================
# 정규식 탐지 (강화 - 띄어쓰기/하이픈 우회 방지)
# ==========================
# 정규식 패턴 캐싱 (모듈 레벨에서 한 번만 컴파일)
COMPILED_PATTERNS = {
    "phone": re.compile(r"\b01[016789][\s\-]?\d{3,4}[\s\-]?\d{4}\b"),
    "email": re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"),
    "birth": re.compile(r"\b(19[0-9]{2}|200[0-6])[년./\- ]+(0?[1-9]|1[0-2])[월./\- ]+(0?[1-9]|[12][0-9]|3[01])[일]?\b"),
    "ssn": re.compile(r"\b\d{6}[\s\-]?[1-4]\d{6}\b"),
    "alien_reg": re.compile(r"\b\d{6}[\s\-]?[5-8]\d{6}\b"),
    "driver_license": re.compile(r"\b\d{2}[\s\-]?\d{2}[\s\-]?\d{6}[\s\-]?\d{2}\b"),
    "passport": re.compile(r"\b[A-Z]\d{2,3}[A-Z]?\d{4,5}\b"),
    "account": re.compile(r"\b\d{6}[\s\-]?\d{2}[\s\-]?\d{6}\b"),
    "card": re.compile(r"\b(?:\d{4}[\s\-]?){3}\d{4}\b"),
    "ip": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
}

COMPILED_NORMALIZED_PATTERNS = {
    "phone_normalized": re.compile(r"\b01[016789]\d{7,8}\b"),
    "ssn_normalized": re.compile(r"\b\d{6}[1-4]\d{6}\b"),
    "alien_reg_normalized": re.compile(r"\b\d{6}[5-8]\d{6}\b"),
    "driver_license_normalized": re.compile(r"\b\d{2}\d{2}\d{6}\d{2}\b"),
    "account_normalized": re.compile(r"\b\d{6}\d{2}\d{6}\b"),
    "card_normalized": re.compile(r"\b\d{16}\b")
}

def detect_by_regex(Text: str) -> list:
    """
    정규식 기반 개인정보 탐지 (우회 방지 강화)
    띄어쓰기, 하이픈 없이도 탐지 가능
    """
    normalized_text = re.sub(r'[\s\-]', '', Text)
    
    detected = []
    
    # 원본 텍스트에서 탐지 (캐싱된 패턴 사용)
    for label, pattern in COMPILED_PATTERNS.items():
        for match in pattern.finditer(Text):
            item = {"type": label, "value": match.group(), "span": match.span()}
            # 카드번호 Luhn 검증
            if label == "card":
                item["status"] = "valid" if validate_luhn(item["value"]) else "invalid (Luhn check failed)"
            # 주민번호 검증
            if label == "ssn":
                item["status"] = "valid" if validate_ssn(item["value"]) else "invalid (SSN check failed)"
            detected.append(item)
    
    # 정규화된 텍스트에서 추가 탐지 (캐싱된 패턴 사용)
    existing_values = {d["value"].replace(" ", "").replace("-", "") for d in detected}
    
    for label, pattern in COMPILED_NORMALIZED_PATTERNS.items():
        original_label = label.replace("_normalized", "")
        for match in pattern.finditer(normalized_text):
            normalized_value = match.group()
            if normalized_value not in existing_values:
                item = {"type": original_label, "value": normalized_value, "span": match.span()}
                # 카드번호 Luhn 검증
                if original_label == "card":
                    item["status"] = "valid" if validate_luhn(item["value"]) else "invalid (Luhn check failed)"
                # 주민번호 검증
                if original_label == "ssn":
                    item["status"] = "valid" if validate_ssn(item["value"]) else "invalid (SSN check failed)"
                detected.append(item)
                existing_values.add(normalized_value)
    
    return detected

# ==========================
# NER 탐지 (조직명 제외)
# ==========================
# 화이트리스트: 탐지하지 않을 이름 목록
NAME_WHITELIST = {
    # 예시: "선우성민", "홍길동", "김철수"
}

# 한국 성씨 목록 (상위 100개)
KOREAN_SURNAMES = {
    '김', '이', '박', '최', '정', '강', '조', '윤', '장', '임',
    '한', '오', '서', '신', '권', '황', '안', '송', '류', '전',
    '홍', '고', '문', '양', '손', '배', '백', '허', '남', '심',
    '노', '하', '곽', '성', '차', '주', '우', '구', '라', '진',
    '유', '나', '변', '염', '방', '원', '천', '공', '현', '함',
    '여', '석', '선', '설', '마', '길', '연', '위', '표', '명',
    '기', '반', '왕', '금', '옥', '육', '인', '맹', '제', '모',
    '탁', '국', '어', '경', '은', '편', '용', '예', '봉', '사',
    '부', '가', '복', '태', '목', '형', '피', '두', '감', '음',
    '빈', '동', '온', '호', '범', '좌', '팽', '승', '간', '견'
}

# 일반 명사 블랙리스트 (이름이 아닌 단어들)
NAME_BLACKLIST = {
    '코딱지', '노홍카', '사과나무', '컴퓨터', '키보드', '마우스',
    '노란색', '파란색', '빨간색', '검은색', '흰색',
    '고양이', '강아지', '토끼', '거북이',
}

def detect_by_ner(Text: str) -> list:
    if not Text.strip():
        return []
    
    # HWP 등에서 추출된 제어 문자 제거 (NER 입력용)
    normalized_text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', Text)
    
    # 한글 단일 글자 띄어쓰기 병합 (예: "이 무 송" -> "이무송")
    # 반복 실행하여 완전히 병합
    while True:
        prev = normalized_text
        normalized_text = re.sub(r'([가-힣])\s+([가-힣])(?=\s|[가-힣]|$)', r'\1\2', normalized_text)
        if prev == normalized_text:
            break
    
    # 정규식으로 이름 추출 ("성명이무송" 패턴)
    name_pattern = re.compile(r'성명([가-힣]{2,4})(?:생년월일|주소|연락처|전화|이메일|E-Mail|휴대폰)')
    name_match = name_pattern.search(normalized_text)
    extracted_name = None
    if name_match:
        extracted_name = name_match.group(1)
        if DEBUG_MODE:
            print(f"[INFO] ✓ 정규식으로 이름 추출: {extracted_name}")
        # 이름 주변에 공백 추가하여 NER이 인식하기 쉽게
        normalized_text = normalized_text.replace(f"성명{extracted_name}", f"성명 {extracted_name} ")
    
    if normalized_text != Text and DEBUG_MODE:
        print(f"[INFO] ⚠ 한글 띄어쓰기 정규화 적용")
        print(f"[DEBUG] 원본: {Text[:200]}")
        print(f"[DEBUG] 정규화: {normalized_text[:200]}")
    
    if DEBUG_MODE:
        print(f"[DEBUG] NER 입력 (최종): {normalized_text[:100]}")
    Results = ner_pipeline(normalized_text)
    if DEBUG_MODE:
        print(f"[DEBUG] NER 원본 결과: {Results}")
    
    # 빈 결과일 경우 문맥 추가해서 재시도 (한글 이름 패턴만)
    if not Results:
        stripped = normalized_text.strip()
        # 2~4글자 한글 + 첫 글자가 한국 성씨 + 블랙리스트 아님
        if (2 <= len(stripped) <= 4 and 
            re.match(r'^[가-힣]+$', stripped) and 
            stripped[0] in KOREAN_SURNAMES and
            stripped not in NAME_BLACKLIST):
            retry_text = f"제 이름은 {stripped}입니다"
            if DEBUG_MODE:
                print(f"[INFO] NER 재시도 (문맥 추가): {retry_text}")
            Results = ner_pipeline(retry_text)
            if DEBUG_MODE:
                print(f"[DEBUG] NER 재시도 결과: {Results}")
    
    Detected = []
    
    # 정규식으로 추출한 이름 먼저 추가
    if extracted_name and extracted_name[0] in KOREAN_SURNAMES:
        Detected.append({"type": "PS", "value": extracted_name, "span": (0, 0)})
        if DEBUG_MODE:
            print(f"[INFO] ✓ 정규식 이름 탐지: {extracted_name}")
    
    # LC (주소) 병합을 위한 임시 저장소
    location_parts = []
    
    for Entity in Results:
        Label = Entity['entity_group']
        Word = Entity['word']
        Start = Entity.get('start')
        End = Entity.get('end')
        
        # ## 접두사 제거
        if Word.startswith('##'):
            Word = Word[2:]
        
        if DEBUG_MODE:
            print(f"[DEBUG] 엔티티: Label={Label}, Word={Word}")
        
        if Start is None or End is None:
            continue
        
        if Label.upper() in ["PER", "PS", "ORG", "LOC", "LC", "MISC"]:
            # LC (주소) 병합 처리
            if Label.upper() == "LC":
                location_parts.append(Word)
                continue
            # PS (사람 이름) 필터링
            if Label.upper() in ["PS", "PER"]:
                # 공백 제거 후 길이 체크
                clean_word = Word.replace(" ", "").strip()
                
                # 너무 짧은 이름 제외 (2글자 이하)
                if len(clean_word) <= 2:
                    if DEBUG_MODE:
                        print(f"[INFO] ✗ NER 필터링 ({Label}): {Word} (2글자 이하)")
                    continue
                
                # 한글 포함 여부 확인
                has_korean = any('\uac00' <= c <= '\ud7a3' for c in Word)
                
                # 숫자만 있는 경우 제외
                if clean_word.isdigit():
                    if DEBUG_MODE:
                        print(f"[INFO] ✗ NER 필터링 ({Label}): {Word} (숫자만 포함)")
                    continue
                
                # 한글이 없고 특수문자만 있는 경우 제외
                if not has_korean and any(c in Word for c in "#@$%^&*()_+=[]{}|\\;:'\",.<>?/~`"):
                    if DEBUG_MODE:
                        print(f"[INFO] ✗ NER 필터링 ({Label}): {Word} (한글 없이 특수문자 포함)")
                    continue
                
                # 화이트리스트 체크
                if clean_word in NAME_WHITELIST:
                    if DEBUG_MODE:
                        print(f"[INFO] ✗ NER 필터링 ({Label}): {Word} (화이트리스트)")
                    continue
                
                # 블랙리스트 체크 (일반 명사 제외)
                if clean_word in NAME_BLACKLIST:
                    if DEBUG_MODE:
                        print(f"[INFO] ✗ NER 필터링 ({Label}): {Word} (블랙리스트 - 일반 명사)")
                    continue
                
                # 불필요한 접두사 제거 (저는, 나는, 제가, 내가 등)
                prefixes_to_remove = ["저는", "나는", "제가", "내가", "저의", "나의", "제", "내"]
                cleaned_name = Word
                for prefix in prefixes_to_remove:
                    if Word.startswith(prefix):
                        cleaned_name = Word[len(prefix):].strip()
                        if DEBUG_MODE:
                            print(f"[INFO] ⚠ NER 접두사 제거: '{Word}' → '{cleaned_name}'")
                        break
                
                # 정리된 이름이 너무 짧으면 제외
                if len(cleaned_name.replace(" ", "")) <= 1:
                    if DEBUG_MODE:
                        print(f"[INFO] ✗ NER 필터링 ({Label}): {Word} (접두사 제거 후 너무 짧음)")
                    continue
                
                # 정리된 이름 저장
                Word = cleaned_name
            
            Detected.append({"type": Label, "value": Word, "span": (Start, End)})
            if DEBUG_MODE:
                print(f"[INFO] ✓ NER 탐지 ({Label}): {Word}")
    
    # 주소 병합
    if location_parts:
        merged_location = ' '.join(location_parts)
        Detected.append({"type": "LC", "value": merged_location, "span": (0, 0)})
        if DEBUG_MODE:
            print(f"[INFO] ✓ 주소 병합: {merged_location}")
    
    return Detected


# ==========================
# 얼굴 탐지 (MTCNN)
# ==========================
def detect_faces_in_image_bytes(image_bytes, confidence_threshold=0.98):
    """이미지에서 얼굴을 탐지합니다 (오탐지 방지 강화)"""
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        # 이미지 크기 체크 (너무 작으면 스킵)
        if img.width < 50 or img.height < 50:
            return []
        
        # 이미지 리사이즈 (얼굴 탐지는 400px면 충분, 속도 2-4배 향상)
        max_size = 400
        if img.width > max_size or img.height > max_size:
            ratio = min(max_size / img.width, max_size / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        
        img_np = np.array(img)
        results = detector.detect_faces(img_np)
        detections = []
        
        for res in results:
            conf = float(res['confidence'])
            x, y, w, h = res['box']
            
            # 필터링 조건
            # 1. confidence >= 0.98 (더 엄격하게)
            if conf < confidence_threshold:
                continue
            
            # 2. 얼굴 크기 검증 (너무 작거나 큰 것 제외)
            if w < 30 or h < 30 or w > img.width * 0.9 or h > img.height * 0.9:
                continue
            
            # 3. 가로세로 비율 검증 (얼굴은 대략 0.7~1.3 비율)
            aspect_ratio = w / h if h > 0 else 0
            if aspect_ratio < 0.6 or aspect_ratio > 1.5:
                continue
            
            # 4. keypoints 검증 (눈, 코, 입이 제대로 탐지되었는지)
            keypoints = res.get('keypoints', {})
            if keypoints:
                left_eye = keypoints.get('left_eye')
                right_eye = keypoints.get('right_eye')
                nose = keypoints.get('nose')
                
                # 눈과 코가 모두 탐지되어야 함
                if not (left_eye and right_eye and nose):
                    continue
                
                # 두 눈 사이 거리 검증
                eye_distance = abs(left_eye[0] - right_eye[0])
                if eye_distance < w * 0.2 or eye_distance > w * 0.8:
                    continue
            
            detections.append({
                "bbox": [int(x), int(y), int(w), int(h)], 
                "confidence": conf
            })
        
        if len(detections) > 0:
            print(f"[INFO] ✓ MTCNN 얼굴 탐지 성공: {len(detections)}개 발견 (필터링 후)")
        return detections
    except Exception as e:
        print(f"[ERROR] MTCNN 얼굴 탐지 실패: {e}")
        return []

# ==========================
# DOCX / PDF 이미지 탐지
# ==========================
def detect_images_in_docx(file_bytes):
    results = []
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as docx_zip:
            image_files = [f for f in docx_zip.namelist() if f.startswith("word/media/")]
            print(f"[INFO] DOCX 내부 이미지 {len(image_files)}개 발견, 얼굴 탐지 시작")
            for image_name in image_files:
                with docx_zip.open(image_name) as image_file:
                    img_bytes = image_file.read()
                    faces = detect_faces_in_image_bytes(img_bytes)
                    if len(faces) > 0:
                        print(f"[INFO] ✓ {image_name} → 얼굴 {len(faces)}개 탐지")
                        results.append({
                            "image_name": image_name,
                            "faces_found": len(faces),
                            "faces": faces
                        })
    except Exception as e:
        print(f"[WARN] DOCX 이미지 검사 실패: {e}")
    return results

def _process_pdf_image(args):
    """PDF 이미지 하나를 처리 (병렬 처리용)"""
    pno, img_index, img_bytes = args
    faces = detect_faces_in_image_bytes(img_bytes)
    if len(faces) > 0:
        print(f"[INFO] ✓ PDF p{pno+1}, img{img_index} → 얼굴 {len(faces)}개 탐지")
        return {
            "page": pno + 1,
            "image_index": img_index,
            "faces_found": len(faces),
            "faces": faces
        }
    return None

def detect_images_in_pdf(pdf_bytes):
    results = []
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            # 중복 이미지 제거 (xref 기반)
            seen_xrefs = set()
            image_tasks = []
            
            for pno, page in enumerate(doc):
                images = page.get_images(full=True)
                if len(images) > 0:
                    print(f"[INFO] PDF 페이지 {pno+1}에서 이미지 {len(images)}개 발견")
                
                for img_index, img in enumerate(images):
                    xref = img[0]
                    
                    # 중복 이미지 스킵 (같은 이미지가 여러 페이지에 반복되는 경우)
                    if xref in seen_xrefs:
                        continue
                    seen_xrefs.add(xref)
                    
                    base_image = doc.extract_image(xref)
                    img_bytes = base_image.get("image")
                    
                    # 너무 작은 이미지 스킵 (로고, 아이콘 등)
                    if img_bytes and len(img_bytes) > 5000:  # 5KB 이상만
                        image_tasks.append((pno, img_index, img_bytes))
            
            # 병렬 처리 (CPU 코어 수에 맞춰 조정)
            if image_tasks:
                print(f"[INFO] 총 {len(image_tasks)}개 이미지를 병렬 처리 시작 (중복 제거 완료)")
                max_workers = min(8, os.cpu_count() or 4)  # CPU 코어 수에 맞춰 동적 조정
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = [executor.submit(_process_pdf_image, task) for task in image_tasks]
                    for future in as_completed(futures):
                        result = future.result()
                        if result:
                            results.append(result)
    except Exception as e:
        print(f"[WARN] PDF 이미지 검사 실패: {e}")
    return results

def detect_images_in_hwp(hwp_bytes):
    """HWP 파일 내부 이미지에서 얼굴 탐지"""
    results = []
    if olefile is None:
        return results
    try:
        ole = olefile.OleFileIO(io.BytesIO(hwp_bytes))
        for entry in ole.listdir():
            if entry[0] == "BinData":
                try:
                    stream = ole.openstream(entry)
                    img_bytes = stream.read()
                    faces = detect_faces_in_image_bytes(img_bytes)
                    if len(faces) > 0:
                        img_name = "/".join(entry)
                        print(f"[INFO] ✓ {img_name} → 얼굴 {len(faces)}개 탐지")
                        results.append({
                            "image_name": img_name,
                            "faces_found": len(faces),
                            "faces": faces
                        })
                except Exception:
                    continue
        ole.close()
    except Exception as e:
        print(f"[WARN] HWP 이미지 검사 실패: {e}")
    return results

def detect_images_in_pptx(pptx_bytes):
    """PPTX 파일 내부 이미지에서 얼굴 탐지"""
    results = []
    try:
        with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as pptx_zip:
            image_files = [f for f in pptx_zip.namelist() if f.startswith("ppt/media/")]
            print(f"[INFO] PPTX 내부 이미지 {len(image_files)}개 발견, 얼굴 탐지 시작")
            for image_name in image_files:
                with pptx_zip.open(image_name) as image_file:
                    img_bytes = image_file.read()
                    faces = detect_faces_in_image_bytes(img_bytes)
                    if len(faces) > 0:
                        print(f"[INFO] ✓ {image_name} → 얼굴 {len(faces)}개 탐지")
                        results.append({
                            "image_name": image_name,
                            "faces_found": len(faces),
                            "faces": faces
                        })
    except Exception as e:
        print(f"[WARN] PPTX 이미지 검사 실패: {e}")
    return results

def scan_file_for_face_images(file_bytes, file_ext):
    """파일 내 이미지에서 얼굴을 탐지합니다"""
    file_ext = file_ext.lower()
    print(f"[INFO] === 얼굴 이미지 스캔 시작 ({file_ext}) ===")
    
    if file_ext == "docx":
        return detect_images_in_docx(file_bytes)
    elif file_ext == "pdf":
        return detect_images_in_pdf(file_bytes)
    elif file_ext == "hwp":
        return detect_images_in_hwp(file_bytes)
    elif file_ext == "pptx":
        return detect_images_in_pptx(file_bytes)
    elif file_ext in ["png", "jpg", "jpeg", "bmp", "webp", "gif", "tiff"]:
        print(f"[INFO] 단일 이미지 파일 얼굴 탐지 시작")
        faces = detect_faces_in_image_bytes(file_bytes)
        if len(faces) > 0:
            return [{
                "image_name": "uploaded_image", 
                "faces_found": len(faces), 
                "faces": faces
            }]
        return []
    else:
        return []

# ==========================
# 최종 핸들러 (마스킹 제거)
# ==========================
def handle_input_raw(Input_Data, Original_Format=None):
    """
    파일을 처리하는 메인 함수
    
    Returns:
        - detected: 탐지된 개인정보 리스트
        - masked_text: 빈 문자열 (마스킹 제거됨)
        - backend_status: 백엔드 전송 성공 여부
        - image_detections: 이미지 내 얼굴 탐지 결과
    """
    if not isinstance(Input_Data, bytes):
        raise ValueError("지원하지 않는 입력 형식입니다.")
    
    print(f"\n[INFO] ========== 파일 처리 시작 (확장자: {Original_Format}) ==========")
    
    # 1단계: 파일 파싱 및 텍스트 추출
    try:
        Parsed_Text, is_pure_image = parse_file(Input_Data, Original_Format)
        Parsed_Text = Parsed_Text.strip()
    except ValueError as ve:
        raise ve
    
    # 2단계: 이미지 내 얼굴 탐지
    image_detections = scan_file_for_face_images(Input_Data, Original_Format or "")
    
    # 3단계: 텍스트에서 개인정보 탐지
    Detected = []
    if Parsed_Text:
        if DEBUG_MODE:
            print(f"[INFO] 텍스트 분석 중... (길이: {len(Parsed_Text)} 글자)")
            print(f"[DEBUG] 텍스트 샘플: {Parsed_Text[:500]}")
        
        # NER 먼저 실행
        ner_results = detect_by_ner(Parsed_Text)
        
        # 정규식 실행
        regex_results = detect_by_regex(Parsed_Text)
        
        # 중복 제거: value 기준으로 중복 제거
        seen = set()
        for item in regex_results + ner_results:
            val = item['value'].strip().lower()
            if val not in seen:
                seen.add(val)
                Detected.append(item)
        
        print(f"[INFO] ✓ 텍스트 개인정보 {len(Detected)}개 탐지 (중복 제거 완료)")
    else:
        print("[INFO] 추출된 텍스트 없음")
    
    # 4단계: 얼굴 탐지 결과를 Detected에 추가
    total_faces = 0
    for img in image_detections:
        face_count = img.get("faces_found", 0)
        total_faces += face_count
        if face_count > 0:
            img_name = img.get("image_name", "이미지")
            Detected.append({
                "type": "image_face",
                "value": f"{img_name} 내 얼굴 {face_count}개",
                "detail": img
            })
    
    if total_faces > 0:
        print(f"[INFO] ✓ 이미지 얼굴 총 {total_faces}개 탐지")
    
    # 5단계: 처리 완료
    if not Detected:
        print("[INFO] ========== 탐지된 민감정보 없음 ==========\n")
    else:
        print(f"[INFO] ========== 처리 완료 - 민감정보: {len(Detected)}개 ==========\n")
    
    return Detected, "", False, image_detections