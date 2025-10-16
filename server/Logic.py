import io
import re
import logging
import numpy as np
import datetime
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import zipfile

# --- 필수 라이브러리 ---
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

# --- 선택 라이브러리 (설치되지 않아도 기본 기능은 동작) ---
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
try:
    import easyocr
except ImportError:
    easyocr = None
try:
    from PIL import Image
except ImportError:
    Image = None
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

# EasyOCR 초기화
reader = None
if easyocr:
    try:
        reader = easyocr.Reader(['ko', 'en'], gpu=False)
        print("[INFO] EasyOCR 초기화 완료")
    except Exception as e:
        print(f"[WARN] EasyOCR 초기화 실패: {e}")
else:
    print("[WARN] easyocr 라이브러리가 설치되지 않았습니다.")

# MTCNN 초기화
detector = None
if MTCNN:
    try:
        detector = MTCNN()
        print("[INFO] MTCNN 초기화 완료")
    except Exception as e:
        print(f"[WARN] MTCNN 초기화 실패: {e}")
else:
    print("[WARN] mtcnn 라이브러리가 설치되지 않았습니다.")


# ==========================
# 검증 함수
# ==========================
def validate_luhn(card_number: str) -> bool:
    """Luhn 알고리즘으로 카드번호 유효성 검사"""
    digits = [int(d) for d in re.sub(r"\D", "", card_number)]
    if len(digits) < 13:
        return False
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            t = d * 2
            checksum += t - 9 if t > 9 else t
        else:
            checksum += d
    return checksum % 10 == 0

def validate_ssn(ssn: str) -> bool:
    """주민등록번호 유효성 검사"""
    ssn = re.sub(r"\D", "", ssn)
    if len(ssn) != 13:
        return False
    
    yy, mm, dd, g = int(ssn[0:2]), int(ssn[2:4]), int(ssn[4:6]), int(ssn[6])
    if g not in [1, 2, 3, 4, 5, 6, 7, 8]:
        return False
    
    century = 1900 if g in [1, 2, 5, 6] else 2000
    try:
        datetime.date(century + yy, mm, dd)
    except ValueError:
        return False

    if (century + yy) >= 2020 and mm >= 10:
        return True

    weights = [2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5]
    s = sum(int(ssn[i]) * weights[i] for i in range(12))
    check_digit = (11 - (s % 11)) % 10
    return check_digit == int(ssn[-1])


# ==========================
# 파일 파싱
# ==========================
def parse_file(File_Bytes: bytes, File_Ext: str) -> tuple:
    """파일을 파싱하여 텍스트를 추출합니다."""
    File_Ext = File_Ext.lower()
    
    if File_Ext == "txt":
        try:
            return File_Bytes.decode("utf-8"), False
        except UnicodeDecodeError:
            return File_Bytes.decode("cp949", errors='ignore'), False

    elif File_Ext == "docx":
        if Document is None: raise ValueError("[ERROR] python-docx 라이브러리 미설치")
        try:
            doc = Document(io.BytesIO(File_Bytes))
            text = "\n".join([para.text for para in doc.paragraphs if para.text])
            for table in doc.tables:
                for row in table.rows:
                    text += "\n" + " ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
            if not text.strip():
                text = run_ocr_on_docx_images(File_Bytes)
            return text, False
        except Exception as e:
            raise ValueError(f"[ERROR] DOCX 파싱 실패: {e}")

    elif File_Ext == "pdf":
        if fitz is None: raise ValueError("[ERROR] PyMuPDF(fitz) 라이브러리 미설치")
        try:
            doc = fitz.open(stream=File_Bytes, filetype="pdf")
            if doc.is_encrypted: raise ValueError("[ERROR] 암호화된 PDF 문서")
            text = " ".join([page.get_text().replace("\n", " ") for page in doc])
            if not any(char.isalnum() for char in text):
                text = run_ocr_on_pdf_images(File_Bytes)
            return text, False
        except Exception as e:
            raise ValueError(f"[ERROR] PDF 파싱 실패: {e}")
    
    elif File_Ext == "hwp":
        if win32com is not None:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".hwp") as tmp:
                    tmp.write(File_Bytes); tmp_path = tmp.name
                hwpx_path = tmp_path + "x"
                hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
                hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
                hwp.Open(tmp_path)
                hwp.SaveAs(hwpx_path, "HWPX"); hwp.Quit()
                with open(hwpx_path, "rb") as f: converted = f.read()
                os.remove(tmp_path); os.remove(hwpx_path)
                return parse_file(converted, "hwpx")
            except Exception as e:
                print(f"[WARN] HWP → HWPX 변환 실패, olefile 방식으로 진행: {e}")
        
        if olefile is None: raise ValueError("[ERROR] olefile 라이브러리 미설치")
        try:
            ole = olefile.OleFileIO(io.BytesIO(File_Bytes))
            text = ""
            if ole.exists("PrvText"):
                text = ole.openstream("PrvText").read().decode("utf-16", errors="ignore").strip()
            if not text.strip():
                for entry in ole.listdir():
                    if entry[0] == "BodyText":
                        try:
                            raw = ole.openstream(entry).read()
                            text += ''.join(c for c in raw.decode("utf-16", errors="ignore") if c.isprintable() or c in '\n\r\t ') + "\n"
                        except: continue
            if not text.strip(): text = run_ocr_on_hwp_images(File_Bytes)
            ole.close()
            return re.sub(r'\s+', ' ', text.strip()), False
        except Exception as e:
            raise ValueError(f"[ERROR] HWP(olefile) 파싱 실패: {e}")
    
    elif File_Ext == "hwpx":
        try:
            with zipfile.ZipFile(io.BytesIO(File_Bytes)) as z:
                sections = [n for n in z.namelist() if n.startswith('Contents/section')]
                if not sections: raise ValueError("[ERROR] HWPX 파싱 실패: XML 파일 없음")
                text = ""
                for name in sections:
                    data = z.read(name).decode("utf-8", errors="ignore")
                    text += re.sub(r'\s+', ' ', re.sub(r"<[^>]+>", " ", data)).strip() + "\n"
                if not text.strip(): text = run_ocr_on_hwpx_images(File_Bytes)
                return text.strip(), False
        except Exception as e:
            raise ValueError(f"[ERROR] HWPX 파싱 실패: {e}")
    
    elif File_Ext in ["xls", "xlsx"]:
        if File_Ext == "xls":
            if win32com is None: raise ValueError("[ERROR] XLS 파싱은 Windows/MS Office 환경 필요")
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xls") as tmp:
                    tmp.write(File_Bytes); tmp_path = tmp.name
                xlsx_path = tmp_path + "x"
                excel = win32com.client.Dispatch("Excel.Application")
                wb = excel.Workbooks.Open(tmp_path)
                wb.SaveAs(xlsx_path, FileFormat=51); wb.Close(SaveChanges=False); excel.Quit()
                with open(xlsx_path, "rb") as f: File_Bytes = f.read()
                os.remove(tmp_path); os.remove(xlsx_path)
            except Exception as e:
                raise ValueError(f"[ERROR] XLS → XLSX 변환 실패: {e}")
        
        if load_workbook is None: raise ValueError("[ERROR] openpyxl 라이브러리 미설치")
        try:
            wb = load_workbook(io.BytesIO(File_Bytes), data_only=True)
            text = ""
            for sheet in wb.worksheets:
                for row in sheet.iter_rows(values_only=True):
                    text += " ".join([str(cell) for cell in row if cell is not None]) + "\n"
            return text.strip(), False
        except Exception as e:
            raise ValueError(f"[ERROR] XLSX 파싱 실패: {e}")
    
    elif File_Ext in ["ppt", "pptx"]:
        if File_Ext == "ppt":
            if win32com is None: raise ValueError("[ERROR] PPT 파싱은 Windows/MS Office 환경 필요")
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".ppt") as tmp:
                    tmp.write(File_Bytes); tmp_path = tmp.name
                pptx_path = tmp_path + "x"
                pp = win32com.client.Dispatch("PowerPoint.Application")
                pres = pp.Presentations.Open(tmp_path, WithWindow=False)
                pres.SaveAs(pptx_path, FileFormat=24); pres.Close(); pp.Quit()
                with open(pptx_path, "rb") as f: File_Bytes = f.read()
                os.remove(tmp_path); os.remove(pptx_path)
            except Exception as e:
                raise ValueError(f"[ERROR] PPT → PPTX 변환 실패: {e}")

        if Presentation is None: raise ValueError("[ERROR] python-pptx 라이브러리 미설치")
        try:
            prs = Presentation(io.BytesIO(File_Bytes))
            text = ""
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"): text += shape.text + "\n"
            text += "\n" + run_ocr_on_pptx_images(File_Bytes)
            return text.strip(), False
        except Exception as e:
            raise ValueError(f"[ERROR] PPTX 파싱 실패: {e}")
    
    elif File_Ext == "doc":
        if win32com is None: raise ValueError("[ERROR] DOC 파싱은 Windows/MS Office 환경 필요")
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".doc") as tmp:
                tmp.write(File_Bytes); tmp_path = tmp.name
            docx_path = tmp_path + "x"
            word = win32com.client.Dispatch("Word.Application")
            doc = word.Documents.Open(tmp_path)
            doc.SaveAs(docx_path, FileFormat=16); doc.Close(); word.Quit()
            with open(docx_path, "rb") as f: converted = f.read()
            os.remove(tmp_path); os.remove(docx_path)
            return parse_file(converted, "docx")
        except Exception as e:
            raise ValueError(f"[ERROR] DOC 파싱 실패: {e}")
    
    elif File_Ext in ["png", "jpg", "jpeg", "bmp", "webp", "gif", "tiff"]:
        return run_ocr_on_single_image(File_Bytes), True
    
    else:
        raise ValueError(f"[ERROR] 지원하지 않는 파일 형식: {File_Ext}")


# ==========================
# OCR
# ==========================
def run_ocr_on_single_image(image_bytes: bytes) -> str:
    if reader is None: return ""
    try:
        result = reader.readtext(np.array(Image.open(io.BytesIO(image_bytes))))
        return "\n".join([box[1] for box in result]).strip()
    except Exception:
        return ""

def _process_ocr_image_task(args):
    return run_ocr_on_single_image(args[1])

def run_ocr_on_docx_images(file_bytes):
    if reader is None: return ""
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            tasks = [(n, z.read(n)) for n in z.namelist() if n.startswith("word/media/")]
            if not tasks: return ""
            with ThreadPoolExecutor() as executor:
                return "\n".join(executor.map(_process_ocr_image_task, tasks))
    except Exception as e:
        print(f"[ERROR] DOCX 이미지 OCR 실패: {e}"); return ""

def run_ocr_on_pdf_images(pdf_bytes: bytes) -> str:
    if reader is None or fitz is None: return ""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        return "\n".join([run_ocr_on_single_image(page.get_pixmap().tobytes("ppm")) for page in doc])
    except Exception as e:
        print(f"[ERROR] PDF 이미지 OCR 실패: {e}"); return ""

def run_ocr_on_hwp_images(hwp_bytes: bytes) -> str:
    if reader is None or olefile is None: return ""
    try:
        ole = olefile.OleFileIO(io.BytesIO(hwp_bytes))
        tasks = [(e, ole.openstream(e).read()) for e in ole.listdir() if e[0] == "BinData"]
        if not tasks: return ""
        with ThreadPoolExecutor() as executor:
            return "\n".join(executor.map(_process_ocr_image_task, tasks))
    except Exception as e:
        print(f"[ERROR] HWP 이미지 OCR 실패: {e}"); return ""

def run_ocr_on_pptx_images(pptx_bytes: bytes) -> str:
    if reader is None: return ""
    try:
        with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as z:
            tasks = [(n, z.read(n)) for n in z.namelist() if n.startswith("ppt/media/")]
            if not tasks: return ""
            with ThreadPoolExecutor() as executor:
                return "\n".join(executor.map(_process_ocr_image_task, tasks))
    except Exception as e:
        print(f"[ERROR] PPTX 이미지 OCR 실패: {e}"); return ""

def run_ocr_on_hwpx_images(hwpx_bytes: bytes) -> str:
    if reader is None: return ""
    try:
        with zipfile.ZipFile(io.BytesIO(hwpx_bytes)) as z:
            tasks = [(n, z.read(n)) for n in z.namelist() if n.startswith("Contents/") and n.lower().endswith((".jpg",".png",".bmp"))]
            if not tasks: return ""
            with ThreadPoolExecutor() as executor:
                return "\n".join(executor.map(_process_ocr_image_task, tasks))
    except Exception as e:
        print(f"[ERROR] HWPX 이미지 OCR 실패: {e}"); return ""


# ==========================
# 정규식 탐지
# ==========================
COMPILED_PATTERNS = {
    "phone": re.compile(r'\b(0\d{1,2}[\s-]*\d{3,4}[\s-]*\d{4})\b'),
    "email": re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"),
    "birth": re.compile(r"\b(1\d{3}|200[0-5])[년./\- ]+(0?[1-9]|1[0-2])[월./\- ]+(0?[1-9]|[12][0-9]|3[01])[일]?\b"),
    "ssn": re.compile(r"\b\d{6}[\s\-]?[1-4]\d{6}\b"),
    "alien_reg": re.compile(r"\b\d{6}[\s\-]?[5-8]\d{6}\b"),
    "driver_license": re.compile(r"\b(1[1-9]|2[0-8])[\s\-]?\d{2}[\s\-]?\d{6}[\s\-]?\d{2}\b"),
    "passport": re.compile(r"\b[A-Z]\d{2,3}[A-Z]?\d{4,5}\b"),
    "account": re.compile(r"\b\d{6}[\s\-]?\d{2}[\s\-]?\d{6}\b"),
    "card": re.compile(r"\b(?:\d{4}[\s\-]?){3}\d{4}\b"),
    "ip": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
}
COMPILED_NORMALIZED_PATTERNS = {
    "phone_normalized": re.compile(r"\b0\d{9,10}\b"),
    "ssn_normalized": re.compile(r"\b\d{6}[1-4]\d{6}\b"),
    "alien_reg_normalized": re.compile(r"\b\d{6}[5-8]\d{6}\b"),
    "driver_license_normalized": re.compile(r"\b(1[1-9]|2[0-8])\d{10}\b"),
    "account_normalized": re.compile(r"\b\d{14}\b"),
    "card_normalized": re.compile(r"\b\d{16}\b")
}

def detect_by_regex(Text: str) -> list:
    normalized_text = re.sub(r'[\s\-]', '', Text)
    detected = []
    
    for label, pattern in COMPILED_PATTERNS.items():
        for match in pattern.finditer(Text):
            item = {"type": label, "value": match.group(), "span": match.span()}
            if label == "card": item["status"] = "valid" if validate_luhn(item["value"]) else "invalid (Luhn)"
            if label == "ssn": item["status"] = "valid" if validate_ssn(item["value"]) else "invalid (SSN)"
            detected.append(item)
    
    existing_values = {re.sub(r'[\s-]', '', d["value"]) for d in detected}
    for label, pattern in COMPILED_NORMALIZED_PATTERNS.items():
        original_label = label.replace("_normalized", "")
        for match in pattern.finditer(normalized_text):
            normalized_value = match.group()
            if normalized_value not in existing_values:
                item = {"type": original_label, "value": normalized_value, "span": match.span()}
                if original_label == "card": item["status"] = "valid" if validate_luhn(item["value"]) else "invalid (Luhn)"
                if original_label == "ssn": item["status"] = "valid" if validate_ssn(item["value"]) else "invalid (SSN)"
                detected.append(item)
                existing_values.add(normalized_value)
    
    return detected


# ==========================
# NER 탐지
# ==========================
NAME_WHITELIST = {}
KOREAN_SURNAMES = {'김', '이', '박', '최', '정', '강', '조', '윤', '장', '임', '한', '오', '서', '신', '권', '황', '안', '송', '류', '전', '홍', '고', '문', '양', '손', '배', '백', '허', '남', '심', '노', '하', '곽', '성', '차', '주', '우', '구', '라', '진'}
NAME_BLACKLIST = {'컴퓨터', '키보드', '마우스'}

def detect_by_ner(Text: str) -> list:
    if not Text.strip(): return []
    Detected = []
    
    name_patterns = re.compile(r"(?:성명|이름)[\s:]*([가-힣]{2,4})\b")
    for match in name_patterns.finditer(Text):
        name = match.group(1)
        if name and name[0] in KOREAN_SURNAMES:
            Detected.append({"type": "NER_PS", "value": name, "span": match.span(1)})
            Text = Text.replace(match.group(0), " ") 

    normalized_text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', Text)
    while True:
        prev = normalized_text
        normalized_text = re.sub(r'([가-힣])\s+([가-힣])(?=\s|[가-힣]|$)', r'\1\2', normalized_text)
        if prev == normalized_text: break
    
    Results = ner_pipeline(normalized_text)
    
    location_parts = []
    for Entity in Results:
        Label, Word = Entity['entity_group'], Entity['word'].replace('##', '')
        if Label.upper() == "LC":
            location_parts.append(Word)
        elif Label.upper() in ["PS", "PER", "ORG", "LOC"]:
            if Label.upper() in ["PS", "PER"]:
                clean_word = Word.replace(" ", "")
                if not any('가' <= char <= '힣' for char in clean_word) and len(clean_word) < 3:
                    continue
                if len(clean_word) <= 1 or clean_word.isdigit() or clean_word in NAME_BLACKLIST:
                    continue
            Detected.append({"type": f"NER_{Label}", "value": Word, "span": (Entity.get('start'), Entity.get('end'))})

    if location_parts:
        unique_parts = list(dict.fromkeys(location_parts))
        Detected.append({"type": "NER_LC", "value": ' '.join(unique_parts), "span": (0, 0)})
    
    return Detected


# ==========================
# 얼굴 탐지
# ==========================
def detect_faces_in_image_bytes(image_bytes, confidence_threshold=0.98):
    if detector is None: return []
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        if img.width < 50 or img.height < 50: return []
        detections = []
        for res in detector.detect_faces(np.array(img)):
            if res['confidence'] < confidence_threshold: continue
            x, y, w, h = res['box']
            if w < 30 or h < 30 or not (0.6 < w/h < 1.5): continue
            if not all(k in res.get('keypoints', {}) for k in ['left_eye', 'right_eye', 'nose']): continue
            detections.append({"bbox": [int(x), int(y), int(w), int(h)], "confidence": float(res['confidence'])})
        return detections
    except Exception:
        return []

def _process_face_detection_task(args):
    faces = detect_faces_in_image_bytes(args[1])
    return {"image_name": args[0], "faces_found": len(faces), "faces": faces} if faces else None

def scan_file_for_face_images(file_bytes, file_ext):
    file_ext = file_ext.lower()
    tasks = []
    try:
        if file_ext in ["png", "jpg", "jpeg", "bmp", "webp", "gif", "tiff"]:
            tasks.append(("uploaded_image", file_bytes))
        elif file_ext in ["docx", "pptx", "hwpx"]:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                prefix = {"docx": "word/media/", "pptx": "ppt/media/"}.get(file_ext, '')
                tasks.extend((n, z.read(n)) for n in z.namelist() if (file_ext != 'hwpx' and n.startswith(prefix)) or (file_ext == 'hwpx' and n.startswith('Contents/') and n.lower().endswith(('.png','.jpg','.jpeg','.bmp','.gif'))))
        elif file_ext == "pdf" and fitz:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            tasks.extend((f"pdf_p{p+1}_img{i+1}", doc.extract_image(img[0])["image"]) for p, page in enumerate(doc) for i, img in enumerate(page.get_images(full=True)) if doc.extract_image(img[0]) and "image" in doc.extract_image(img[0]))
        elif file_ext == "hwp" and olefile:
            ole = olefile.OleFileIO(io.BytesIO(file_bytes))
            tasks.extend(("/".join(e), ole.openstream(e).read()) for e in ole.listdir() if e[0] == "BinData")
    except Exception as e:
        print(f"[WARN] {file_ext.upper()} 이미지 추출 실패: {e}")

    if not tasks: return []
    with ThreadPoolExecutor() as executor:
        return [r for r in executor.map(_process_face_detection_task, tasks) if r]


# ==========================
# 최종 핸들러
# ==========================
def handle_input_raw(Input_Data, Original_Format=None):
    if not isinstance(Input_Data, bytes):
        raise ValueError("지원하지 않는 입력 형식입니다.")
    
    print(f"\n[INFO] ========== 파일 처리 시작 (확장자: {Original_Format}) ==========")
    
    Parsed_Text, _ = parse_file(Input_Data, Original_Format or "")
    image_detections = scan_file_for_face_images(Input_Data, Original_Format or "")
    
    detected_items = []
    if Parsed_Text:
        print(f"[INFO] 텍스트 분석 중... (길이: {len(Parsed_Text)} 글자)")
        detected_items.extend(detect_by_ner(Parsed_Text))
        detected_items.extend(detect_by_regex(Parsed_Text))
    
    for img_res in image_detections:
        detected_items.append({"type": "image_face", "value": f"{img_res.get('image_name', '이미지')} 내 얼굴 {img_res.get('faces_found', 0)}개", "detail": img_res})

    final_detected, seen_values = [], set()
    for item in detected_items:
        val = re.sub(r'[\s-]', '', item['value']).lower()
        if item['type'].startswith("NER_"): val = val.replace(" ", "")
        if val not in seen_values:
            final_detected.append(item)
            seen_values.add(val)
    
    print(f"[INFO] ✓ 최종 탐지된 민감정보: {len(final_detected)}개 (중복 제거 완료)\n")
    return final_detected, "", False, image_detections