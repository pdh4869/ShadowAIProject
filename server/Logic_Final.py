# =============================
# File: Logic_Final.py (NER 예외 처리 및 기능 개선 최종 버전)
# Desc: SC 버전을 베이스로 통합. logic.py의 파일명 마스킹 로직을 채택.
#       SC의 조합위험도/병렬/얼굴탐지/디버그를 유지하면서
#       Logic.py 및 Logic_Merged_NoBack.py에 있던 누락 기능 보완.
#       조합 위험도 분석 로그 상세화, 국제 전화번호 탐지, 전화번호 중복 탐지 문제 해결,
#       카드 번호 오탐지 문제 보완 및 NER 후처리 로직으로 회사명 오탐지 수정.
# =============================

import io
import re
import os
import logging
import zipfile
import tempfile
import datetime
import numpy as np
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

# --- 필수 라이브러리 ---
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

# --- 선택 라이브러리 (설치되지 않아도 기본 기능 동작) ---
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

# 로깅
DEBUG_MODE = os.getenv("PII_DEBUG", "false").lower() == "true"
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='[%(levelname)s] %(message)s'
)

# ==========================
# NER 모델 로딩
# ==========================
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
if easyocr and Image is not None:
    try:
        reader = easyocr.Reader(['ko', 'en'], gpu=False)
        print("[INFO] EasyOCR 초기화 완료")
    except Exception as e:
        print(f"[WARN] EasyOCR 초기화 실패: {e}")
else:
    print("[WARN] EasyOCR 또는 PIL 미설치")

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
# 검증 함수 (Luhn/주민등록)
# ==========================

def validate_luhn(card_number: str) -> bool:
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
    ssn = re.sub(r"\D", "", ssn)
    if len(ssn) != 13:
        return False
    yy, mm, dd, g = int(ssn[0:2]), int(ssn[2:4]), int(ssn[4:6]), int(ssn[6])
    if g not in [1,2,3,4,5,6,7,8]:
        return False
    century = 1900 if g in [1,2,5,6] else 2000
    try:
        datetime.date(century + yy, mm, dd)
    except ValueError:
        return False
    # 2020년 이후 출생자 일부 예외 허용
    if (century + yy) >= 2020:
        return True
    weights = [2,3,4,5,6,7,8,9,2,3,4,5]
    s = sum(int(ssn[i]) * weights[i] for i in range(12))
    check_digit = (11 - (s % 11)) % 10
    return check_digit == int(ssn[-1])

# ==========================
# 정규식 패턴 (Logic.py 기반, SC에서 사용)
# ==========================

COMPILED_PATTERNS = {
    "phone": re.compile(r'(?<!\d)((?:\+82[\s-]?)?0?10|\+82[\s-]?\d{1,2}|0\d{1,2})[\s-]?\d{3,4}[\s-]?\d{4}(?!\d)'),
    "email": re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
    "birth": re.compile(r"(?<!\d)(1\d{3}|200[0-5])[년./\- ]+(0?[1-9]|1[0-2])[월./\- ]+(0?[1-9]|[12][0-9]|3[01])[일]?(?!\d)"),
    "ssn": re.compile(r"(?<!\d)\d{6}[\s\-]?[1-4]\d{6}(?!\d)"),
    "alien_reg": re.compile(r"(?<!\d)\d{6}[\s\-]?[5-8]\d{6}(?!\d)"),
    "driver_license": re.compile(r"(?<!\d)(1[1-9]|2[0-8])[\s\-]?\d{2}[\s\-]?\d{6}[\s\-]?\d{2}(?!\d)"),
    "passport": re.compile(r"\b[A-Z]\d{2,3}[A-Z]?\d{4,5}\b"),
    "account": re.compile(r"(?<!\d)\d{6}[\s\-]?\d{2}[\s\-]?\d{6}(?!\d)"),
    "card": re.compile(r"(?<!\d)(?:\d{4}[\s\-]?){3}\d{4}(?!\d)"),
    "ip": re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")
}
COMPILED_NORMALIZED_PATTERNS = {
    "phone_normalized": re.compile(r"(?<!\d)(?:\+?82|0)\d{9,11}(?!\d)"),
    "ssn_normalized": re.compile(r"(?<!\d)\d{6}[1-4]\d{6}(?!\d)"),
    "alien_reg_normalized": re.compile(r"(?<!\d)\d{6}[5-8]\d{6}(?!\d)"),
    "driver_license_normalized": re.compile(r"(?<!\d)(1[1-9]|2[0-8])\d{10}(?!\d)"),
    "account_normalized": re.compile(r"(?<!\d)\d{14}(?!\d)"),
    "card_normalized": re.compile(r"(?<!\d)\d{16}(?!\d)")
}

KOREAN_SURNAMES = {'김','이','박','최','정','강','조','윤','장','임','한','오','서','신','권','황','안','송','류','전','홍','고','문','양','손','배','백','허','남','심','노','하','곽','성','차','주','우','구','라','진'}
NAME_BLACKLIST = {'컴퓨터','키보드','마우스'}

# ==========================
# 파일명 마스킹 (Logic.py 로직 이식)
# ==========================

def mask_pii_in_filename(filename: str) -> tuple:
    detected_items = detect_by_regex(filename)
    detected_items.extend(detect_by_ner(filename))

    if not detected_items:
        return (filename, None)

    unique_items = []
    detected_items.sort(key=lambda x: x.get('span', (9999, 9999))[0])
    last_end = -1
    for item in detected_items:
        span = item.get('span')
        if not span:
            continue
        s, e = span
        if s >= last_end:
            unique_items.append(item)
            last_end = e

    if not unique_items:
        return (filename, None)

    type_map = {
        'ssn': '주민등록번호','email':'이메일','phone':'전화번호','card':'카드번호',
        'driver_license':'운전면허','account':'계좌번호','passport':'여권번호','alien_reg':'외국인등록번호'
    }
    detected_types = set()
    for it in unique_items:
        t = it.get('type','')
        display_type = '이름' if t in ['PS','PER','NER_PS','NER_PER'] else type_map.get(t, t)
        detected_types.add(display_type)

    masked = filename
    unique_items.sort(key=lambda x: x.get('span', (0,0))[1], reverse=True)
    for it in unique_items:
        s, e = it.get('span', (None,None))
        if s is None:
            continue
        val = it.get('value','')
        masked = masked[:s] + ('*' * len(val)) + masked[e:]

    return (masked, ', '.join(sorted(detected_types)) if detected_types else None)

# ==========================
# 정규식 / NER / 준식별자
# ==========================

def detect_by_regex(Text: str) -> list:
    normalized_text = re.sub(r'[\s\-]', '', Text)
    detected = []
    for label, pattern in COMPILED_PATTERNS.items():
        for match in pattern.finditer(Text):
            item = {"type": label, "value": match.group(), "span": match.span()}
            if label == "card":
                item["status"] = "valid" if validate_luhn(item["value"]) else "invalid (Luhn)"
            if label == "ssn":
                item["status"] = "valid" if validate_ssn(item["value"]) else "invalid (SSN)"
            detected.append(item)

    existing = set()
    for d in detected:
        normalized_val = re.sub(r'[\s-]', '', d["value"])
        existing.add(normalized_val)
        if d["type"] == "phone" and normalized_val.startswith('+'):
            existing.add(normalized_val[1:])

    for label, pattern in COMPILED_NORMALIZED_PATTERNS.items():
        original = label.replace("_normalized", "")
        for m in pattern.finditer(normalized_text):
            nv = m.group()
            if nv in existing:
                continue
            if original == "phone" and not nv.startswith('+') and f"+{nv}" in existing:
                continue

            vp = re.compile(r'[\s-]*'.join(list(nv)))
            rm = vp.search(Text)
            if rm:
                original_value = rm.group()
                if original == "card" and re.search(r'\d{4}[\s-]\d{2}[\s-]\d{2}', original_value):
                    continue

                item = {"type": original, "value": original_value, "span": rm.span()}
                if original == "card":
                    item["status"] = "valid" if validate_luhn(item["value"]) else "invalid (Luhn)"
                if original == "ssn":
                    item["status"] = "valid" if validate_ssn(item["value"]) else "invalid (SSN)"
                detected.append(item)
                existing.add(nv)
            else:
                detected.append({"type": original, "value": nv, "span": None})
                existing.add(nv)
    return detected


def detect_by_ner(Text: str) -> list:
    if not Text.strip():
        return []
        
    # --- Step 1: Rule-based ORG pre-detection ---
    rule_results = []
    # Company names like 삼성전자, LG화학
    company_keywords = ["전자", "화학", "건설", "중공업", "금융", "증권", "생명", "화재", "카드", "닷컴", "그룹", "홀딩스"]
    company_pattern_text = r'\b([가-힣A-Za-z0-9]{2,})(' + '|'.join(company_keywords) + r')\b'
    for match in re.finditer(company_pattern_text, Text):
        rule_results.append({"type": "ORG", "value": match.group(), "span": match.span()})
    # Department names like 개발팀, 인사부
    for match in re.finditer(r'\b([가-힣A-Za-z0-9]+(?:팀|부|실|본부|그룹|센터))\b', Text):
        rule_results.append({"type": "ORG", "value": match.group(), "span": match.span()})

    # --- Step 2: NER Pipeline ---
    ner_results = []
    try:
        # Pre-process for NER: remove control characters
        normalized_text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', Text)
        ner_pipeline_results = ner_pipeline(normalized_text)

        # Convert pipeline results to our standard format
        for entity in ner_pipeline_results:
            if 'start' not in entity or 'end' not in entity: continue
            ner_results.append({
                "type": entity['entity_group'],
                "value": entity['word'].replace('##', ''),
                "span": (entity.get('start'), entity.get('end'))
            })
    except Exception as e:
        logging.warning(f"NER 파이프라인 오류: {e}")

    # --- Step 3: Merge and resolve conflicts (Rule > NER) ---
    final_results = []
    ner_spans_to_discard = set()

    # If a rule-based ORG overlaps with a NER result, the rule wins.
    for rule_item in rule_results:
        rule_start, rule_end = rule_item['span']
        for i, ner_item in enumerate(ner_results):
            ner_start, ner_end = ner_item['span']
            # Check for any overlap
            if ner_start < rule_end and ner_end > rule_start:
                # Mark the NER span to be discarded
                ner_spans_to_discard.add(ner_item['span'])

    # Add the winning rule-based items
    final_results.extend(rule_results)

    # Add NER items that were not discarded
    for ner_item in ner_results:
        if ner_item['span'] not in ner_spans_to_discard:
            final_results.append(ner_item)
            
    # --- Step 4: Final filtering and formatting ---
    output_detections = []
    location_parts = []

    # Add pre-detected names from patterns like "성명: 김철수"
    name_patterns = re.compile(r"(?:성명|이름)[\s:]*([가-힣]{2,4})\b")
    for match in name_patterns.finditer(Text):
        name = match.group(1)
        if name and name[0] in KOREAN_SURNAMES:
            output_detections.append({"type": "PS", "value": name, "span": match.span(1)})

    for entity in final_results:
        Label = entity['type'].upper()
        Word = entity['value']

        if Label == 'LC':
            location_parts.append(Word)
            continue
        if Label in ['PS','PER']:
            clean = Word.replace(' ', '')
            if len(clean) <= 1 or clean.isdigit() or clean in NAME_BLACKLIST:
                continue
        if Label in ['PS','PER','ORG','LOC']:
            output_detections.append(entity)

    if location_parts:
        uniq = list(dict.fromkeys(location_parts))
        # Span for location is tricky as it's aggregated, set to (0,0) as before
        output_detections.append({"type": "LC", "value": ' '.join(uniq), "span": (0,0)})

    # Final de-duplication based on span to ensure no overlaps in the final output
    deduplicated_final = []
    sorted_output = sorted(output_detections, key=lambda x: x['span'][0])
    last_end = -1
    for item in sorted_output:
        start, end = item['span']
        if start >= last_end:
            deduplicated_final.append(item)
            last_end = end

    return deduplicated_final


def detect_quasi_identifiers(text: str) -> list:
    detected = []
    id_pattern = re.compile(r'\b(19|20|24)\d{5,8}\b')
    for m in id_pattern.finditer(text):
        start, end = m.span()
        if (start > 0 and text[start-1].isalpha()) or (end < len(text) and text[end].isalpha()):
            continue
        detected.append({"type":"student_id","value":m.group(),"span":(start,end)})
    position_pattern = re.compile(r'\b(교수|팀장|부장|과장|대리|사원|이사|본부장|실장|차장|주임|연구원|박사|석사|회장|사장|전무|상무|부사장|대표|원장|소장|센터장)\b')
    for m in position_pattern.finditer(text):
        detected.append({"type":"position","value":m.group(),"span":m.span()})
    return detected

# ==========================
# 조합 위험도 (SC + 상세 로그 버전)
# ==========================

def _category(item_type: str) -> str:
    if item_type in ['PS','PER','image_face', 'phone', 'email', 'ssn', 'alien_reg', 'driver_license', 'passport', 'card', 'account']:
        return 'identifier'
    if item_type in ['ORG','OG','student_id','birth','LC','position', 'ip', 'LOC']:
        return 'quasi'
    return 'other'

def _translate_type(item_type: str) -> str:
    type_map = {
        'PS': '이름', 'PER': '이름', 'image_face': '얼굴',
        'phone': '전화번호', 'email': '이메일', 'ssn': '주민번호',
        'alien_reg': '외국인번호', 'driver_license': '면허번호',
        'passport': '여권번호', 'card': '카드번호', 'account': '계좌번호',
        'ORG': '조직명', 'OG': '조직명', 'student_id': '학번', 'birth': '생년월일',
        'LC': '지역명', 'LOC': '지역명', 'position': '직위', 'ip': 'IP'
    }
    return type_map.get(item_type, item_type)

def analyze_combination_risk(detected_items, text):
    if len(detected_items) < 2:
        return None

    categorized = {}
    for it in detected_items:
        cat = _category(it.get('type',''))
        categorized.setdefault(cat, []).append(it)

    identifiers = categorized.get('identifier', [])
    quasis = categorized.get('quasi', [])
    id_cnt = len(identifiers)
    q_cnt = len(quasis)
    
    id_types = Counter([_translate_type(i['type']) for i in identifiers])
    q_types = Counter([_translate_type(i['type']) for i in quasis])

    risk_level = None
    risk_msg = None
    risk_items = []

    if id_cnt >= 1 and q_cnt >= 2:
        risk_level = 'high'
        id_str = ",".join(id_types.keys())
        q_str = ",".join(q_types.keys())
        risk_msg = f'식별자({id_str}){id_cnt}건+준식별자({q_str}){q_cnt}건 → 개인 특정 가능'
        risk_items = identifiers + quasis
    elif id_cnt >= 1 and q_cnt >= 1:
        risk_level = 'medium'
        id_str = ",".join(id_types.keys())
        q_str = ",".join(q_types.keys())
        risk_msg = f'식별자({id_str}){id_cnt}건+준식별자({q_str}){q_cnt}건 → 개인 특정 가능성'
        risk_items = identifiers + quasis
    elif q_cnt >= 3:
        risk_level = 'medium'
        q_str = ",".join(q_types.keys())
        risk_msg = f'준식별자({q_str}){q_cnt}건 조합 → 개인 특정 가능성'
        risk_items = quasis
    
    if risk_level:
        return {
            'level': risk_level,
            'message': risk_msg,
            'items': risk_items,
            'counts': {'identifier': id_cnt, 'quasi': q_cnt}
        }
    return None

# ==========================
# OCR
# ==========================

def run_ocr_on_single_image(image_bytes: bytes) -> str:
    if reader is None or Image is None:
        return ""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        result = reader.readtext(np.array(img))
        return "\n".join([b[1] for b in result]).strip()
    except Exception as e:
        print(f"[ERROR] 이미지 OCR 실패: {e}")
        return ""


def _ocr_task(args):
    return run_ocr_on_single_image(args[1])


def run_ocr_on_docx_images(file_bytes):
    if reader is None:
        return ""
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            tasks = [(n, z.read(n)) for n in z.namelist() if n.startswith("word/media/")]
            if not tasks:
                return ""
            with ThreadPoolExecutor() as ex:
                return "\n".join(ex.map(_ocr_task, tasks))
    except Exception as e:
        print(f"[ERROR] DOCX 이미지 OCR 실패: {e}")
        return ""


def run_ocr_on_pdf_images(pdf_bytes: bytes) -> str:
    if reader is None or fitz is None:
        return ""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        texts = []
        for page in doc:
            pix = page.get_pixmap()
            texts.append(run_ocr_on_single_image(pix.tobytes("ppm")))
        return "\n".join(texts)
    except Exception as e:
        print(f"[ERROR] PDF 이미지 OCR 실패: {e}")
        return ""


def run_ocr_on_hwp_images(hwp_bytes: bytes) -> str:
    if reader is None or olefile is None:
        return ""
    try:
        ole = olefile.OleFileIO(io.BytesIO(hwp_bytes))
        tasks = [(e, ole.openstream(e).read()) for e in ole.listdir() if e[0] == "BinData"]
        if not tasks:
            return ""
        with ThreadPoolExecutor() as ex:
            return "\n".join(ex.map(_ocr_task, tasks))
    except Exception as e:
        print(f"[ERROR] HWP 이미지 OCR 실패: {e}")
        return ""


def run_ocr_on_pptx_images(pptx_bytes: bytes) -> str:
    if reader is None:
        return ""
    try:
        with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as z:
            tasks = [(n, z.read(n)) for n in z.namelist() if n.startswith("ppt/media/")]
            if not tasks:
                return ""
            with ThreadPoolExecutor() as ex:
                return "\n".join(ex.map(_ocr_task, tasks))
    except Exception as e:
        print(f"[ERROR] PPTX 이미지 OCR 실패: {e}")
        return ""


def run_ocr_on_hwpx_images(hwpx_bytes: bytes) -> str:
    if reader is None:
        return ""
    try:
        with zipfile.ZipFile(io.BytesIO(hwpx_bytes)) as z:
            tasks = [(n, z.read(n)) for n in z.namelist() if n.startswith("Contents/") and n.lower().endswith((".jpg",".png",".bmp",".jpeg",".gif"))]
            if not tasks:
                return ""
            with ThreadPoolExecutor() as ex:
                return "\n".join(ex.map(_ocr_task, tasks))
    except Exception as e:
        print(f"[ERROR] HWPX 이미지 OCR 실패: {e}")
        return ""

# ==========================
# 파일 파싱 (SC+Logic 통합)
# ==========================

def parse_file(File_Bytes: bytes, File_Ext: str) -> tuple:
    File_Ext = (File_Ext or '').lower()

    if File_Ext == "txt":
        try:
            return File_Bytes.decode("utf-8"), False
        except UnicodeDecodeError:
            return File_Bytes.decode("cp949", errors='ignore'), False

    elif File_Ext == "docx":
        if Document is None:
            raise ValueError("[ERROR] python-docx 라이브러리 미설치")
        try:
            doc = Document(io.BytesIO(File_Bytes))
            text = "\n".join([p.text for p in doc.paragraphs if p.text])
            for table in doc.tables:
                for row in table.rows:
                    text += "\n" + " ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
            if not text.strip():
                text = run_ocr_on_docx_images(File_Bytes)
            return re.sub(r'\s+', ' ', text.strip()), False
        except Exception as e:
            raise ValueError(f"[ERROR] DOCX 파싱 실패: {e}")

    elif File_Ext == "pdf":
        if fitz is None:
            raise ValueError("[ERROR] PyMuPDF(fitz) 라이브러리 미설치")
        try:
            doc = fitz.open(stream=File_Bytes, filetype="pdf")
            if doc.is_encrypted:
                raise ValueError("[ERROR] 암호화된 PDF 문서")
            text = " ".join([page.get_text().replace("\n"," ") for page in doc])
            if not any(ch.isalnum() for ch in text):
                text = run_ocr_on_pdf_images(File_Bytes)
            return text.strip(), False
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
                with open(hwpx_path, "rb") as f:
                    converted = f.read()
                os.remove(tmp_path); os.remove(hwpx_path)
                return parse_file(converted, "hwpx")
            except Exception as e:
                print(f"[WARN] HWP → HWPX 변환 실패, olefile 방식으로 진행: {e}")
        if olefile is None:
            raise ValueError("[ERROR] olefile 라이브러리 미설치")
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
                        except Exception:
                            continue
            if not text.strip():
                text = run_ocr_on_hwp_images(File_Bytes)
            ole.close()
            return re.sub(r'\s+', ' ', text.strip()), False
        except Exception as e:
            raise ValueError(f"[ERROR] HWP(olefile) 파싱 실패: {e}")

    elif File_Ext == "hwpx":
        try:
            with zipfile.ZipFile(io.BytesIO(File_Bytes)) as z:
                sections = [n for n in z.namelist() if n.startswith('Contents/section')]
                if not sections:
                    xmls = [n for n in z.namelist() if n.endswith('.xml')]
                    text = ''
                    for name in xmls:
                        data = z.read(name).decode('utf-8', errors='ignore')
                        text += re.sub('<[^>]+>', ' ', data)
                else:
                    text = ''
                    for name in sections:
                        data = z.read(name).decode('utf-8', errors='ignore')
                        text += re.sub('<[^>]+>', ' ', data)
                text = re.sub(r'\s+', ' ', text).strip()
                if not text:
                    text = run_ocr_on_hwpx_images(File_Bytes)
                return text.strip(), False
        except Exception as e:
            raise ValueError(f"[ERROR] HWPX 파싱 실패: {e}")

    elif File_Ext in ["xls","xlsx"]:
        if File_Ext == "xls":
            if win32com is None:
                raise ValueError("[ERROR] XLS 파싱은 Windows/MS Office 환경 필요")
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xls") as tmp:
                    tmp.write(File_Bytes); tmp_path = tmp.name
                xlsx_path = tmp_path + "x"
                excel = win32com.client.Dispatch("Excel.Application")
                wb = excel.Workbooks.Open(tmp_path)
                wb.SaveAs(xlsx_path, FileFormat=51); wb.Close(SaveChanges=False); excel.Quit()
                with open(xlsx_path, "rb") as f:
                    File_Bytes = f.read()
                os.remove(tmp_path); os.remove(xlsx_path)
            except Exception as e:
                raise ValueError(f"[ERROR] XLS → XLSX 변환 실패: {e}")
        if load_workbook is None:
            raise ValueError("[ERROR] openpyxl 라이브러리 미설치")
        try:
            wb = load_workbook(io.BytesIO(File_Bytes), data_only=True)
            text = ""
            for sheet in wb.worksheets:
                for row in sheet.iter_rows(values_only=True):
                    text += " ".join([str(c) for c in row if c is not None]) + "\n"
            return text.strip(), False
        except Exception as e:
            raise ValueError(f"[ERROR] XLSX 파싱 실패: {e}")

    elif File_Ext in ["ppt","pptx"]:
        if File_Ext == "ppt":
            if win32com is None:
                raise ValueError("[ERROR] PPT 파싱은 Windows/MS Office 환경 필요")
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".ppt") as tmp:
                    tmp.write(File_Bytes); tmp_path = tmp.name
                pptx_path = tmp_path + "x"
                pp = win32com.client.Dispatch("PowerPoint.Application")
                pres = pp.Presentations.Open(tmp_path, WithWindow=False)
                pres.SaveAs(pptx_path, FileFormat=24); pres.Close(); pp.Quit()
                with open(pptx_path, "rb") as f:
                    File_Bytes = f.read()
                os.remove(tmp_path); os.remove(pptx_path)
            except Exception as e:
                raise ValueError(f"[ERROR] PPT → PPTX 변환 실패: {e}")
        if Presentation is None:
            raise ValueError("[ERROR] python-pptx 라이브러리 미설치")
        try:
            prs = Presentation(io.BytesIO(File_Bytes))
            text = ""
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, 'text'):
                        text += shape.text + "\n"
            ocr = run_ocr_on_pptx_images(File_Bytes)
            if ocr:
                text += "\n" + ocr
            return text.strip(), False
        except Exception as e:
            raise ValueError(f"[ERROR] PPTX 파싱 실패: {e}")

    elif File_Ext in ["png","jpg","jpeg","bmp","webp","gif","tiff"]:
        return run_ocr_on_single_image(File_Bytes), True

    else:
        raise ValueError(f"[ERROR] 지원하지 않는 파일 형식: {File_Ext}")

# ==========================
# 얼굴 탐지 (SC 유지 + 병렬)
# ==========================

def detect_faces_in_image_bytes(image_bytes, confidence_threshold=0.98):
    if detector is None or Image is None:
        return []
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        if img.width < 50 or img.height < 50:
            return []
        # 크기 제한으로 속도 개선
        max_size = 800
        if img.width > max_size or img.height > max_size:
            r = min(max_size / img.width, max_size / img.height)
            img = img.resize((int(img.width*r), int(img.height*r)))
        detections = []
        for res in detector.detect_faces(np.array(img)):
            conf = float(res.get('confidence', 0))
            if conf < confidence_threshold:
                continue
            x,y,w,h = res['box']
            if w < 30 or h < 30 or not (0.6 < (w/h) < 1.5):
                continue
            k = res.get('keypoints', {})
            if not all(p in k for p in ['left_eye','right_eye','nose']):
                continue
            detections.append({"bbox":[int(x),int(y),int(w),int(h)], "confidence": conf})
        return detections
    except Exception as e:
        print(f"[ERROR] 얼굴 탐지 실패: {e}")
        return []


def _face_task(args):
    name, bytes_ = args
    faces = detect_faces_in_image_bytes(bytes_)
    return {"image_name": name, "faces_found": len(faces), "faces": faces} if faces else None


def scan_file_for_face_images(file_bytes, file_ext):
    file_ext = (file_ext or '').lower()
    tasks = []
    try:
        if file_ext in ["png","jpg","jpeg","bmp","webp","gif","tiff"]:
            tasks.append(("uploaded_image", file_bytes))
        elif file_ext in ["docx","pptx","hwpx"]:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                if file_ext == 'docx':
                    prefix = 'word/media/'
                    imgs = [n for n in z.namelist() if n.startswith(prefix)]
                elif file_ext == 'pptx':
                    prefix = 'ppt/media/'
                    imgs = [n for n in z.namelist() if n.startswith(prefix)]
                else:  # hwpx
                    imgs = [n for n in z.namelist() if n.startswith('Contents/') and n.lower().endswith((".png",".jpg",".jpeg",".bmp",".gif"))]
                tasks.extend((n, z.read(n)) for n in imgs)
        elif file_ext == 'pdf' and fitz:
            doc = fitz.open(stream=file_bytes, filetype='pdf')
            seen = set()
            for p, page in enumerate(doc):
                for i, img in enumerate(page.get_images(full=True)):
                    xref = img[0]
                    if xref in seen:
                        continue
                    seen.add(xref)
                    bi = doc.extract_image(xref)
                    if not bi or 'image' not in bi or len(bi['image']) < 5000:
                        continue
                    tasks.append((f"pdf_p{p+1}_img{i+1}", bi['image']))
        elif file_ext == 'hwp' and olefile:
            ole = olefile.OleFileIO(io.BytesIO(file_bytes))
            tasks.extend(("/".join(e), ole.openstream(e).read()) for e in ole.listdir() if e[0]=='BinData')
    except Exception as e:
        print(f"[WARN] {file_ext.upper()} 이미지 추출 실패: {e}")
    if not tasks:
        return []
    with ThreadPoolExecutor(max_workers=min(8, (os.cpu_count() or 4))) as ex:
        return [r for r in ex.map(_face_task, tasks) if r]

# ==========================
# 메인 핸들러 (SC 스타일 + 파일명 마스킹 반환)
# ==========================

def handle_input_raw(Input_Data: bytes, Original_Format: str = None, Original_Filename: str = None):
    if not isinstance(Input_Data, bytes):
        raise ValueError("지원하지 않는 입력 형식입니다.")
    print(f"\n[INFO] ========== 파일 처리 시작 (확장자: {Original_Format}) ==========")

    Parsed_Text, is_image_only = parse_file(Input_Data, Original_Format or "")
    image_detections = scan_file_for_face_images(Input_Data, Original_Format or "")

    Detected = []

    # 텍스트 기반 탐지 (파일명 포함하여 문맥 탐지 강화)
    combined_text = Parsed_Text or ""
    if Original_Filename:
        base = Original_Filename.rsplit('.', 1)[0]
        combined_text = (base + " \n" + combined_text).strip()

    if combined_text:
        ner_results   = detect_by_ner(combined_text)
        regex_results = detect_by_regex(combined_text)
        quasi_results = detect_quasi_identifiers(combined_text)
        # 중복 제거 (value 기준)
        all_detected, seen = [], set()
        for it in (regex_results + ner_results + quasi_results):
            v = (it.get('value','').strip().lower())
            if v and v not in seen:
                seen.add(v)
                all_detected.append(it)
        comb = analyze_combination_risk(all_detected, combined_text)
        if comb:
            Detected = all_detected
            Detected.append({
                "type":"combination_risk",
                "value": comb['message'],
                "risk_level": comb['level'],
                "risk_items": comb['items'],
                "counts": comb['counts']
            })
        else:
            Detected = [i for i in all_detected if i.get('type') not in ['ORG','OG','student_id','birth','LC']]

    # 얼굴 탐지 추가
    total_faces = 0
    for img in image_detections:
        cnt = img.get('faces_found', 0)
        total_faces += cnt
        if cnt > 0:
            Detected.append({"type":"image_face","value":f"{img.get('image_name','이미지')} 내 얼굴 {cnt}개","detail":img})
    if total_faces > 0:
        print(f"[INFO] ✓ 이미지 얼굴 총 {total_faces}개 탐지")

    # 파일명 마스킹 결과
    masked_filename = None
    if Original_Filename:
        masked, types = mask_pii_in_filename(Original_Filename)
        masked_filename = masked if masked != Original_Filename else None

    # 백엔드 전송 여부(하위호환)
    backend_status = True

    return Detected, (masked_filename or ""), backend_status, image_detections