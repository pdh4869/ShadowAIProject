import io
import re
import requests
import logging
import cv2
import numpy as np
import fitz
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from docx import Document
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from docx.oxml.ns import qn
from docx.shared import Pt

Key = b"1234567890abcdef"
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
NER_MODEL_NAME = "xlm-roberta-large-finetuned-conll03-english" # 성공!!!!
ner_tokenizer = AutoTokenizer.from_pretrained(NER_MODEL_NAME)
ner_model = AutoModelForTokenClassification.from_pretrained(NER_MODEL_NAME)
ner_pipeline = pipeline("ner", model=ner_model, tokenizer=ner_tokenizer, grouped_entities=True)

def parse_file(File_Bytes: bytes, File_Ext: str) -> str:
    File_Ext = File_Ext.lower()

    if File_Ext == "txt":
        try:
            return File_Bytes.decode("utf-8")
        except UnicodeDecodeError:
            return File_Bytes.decode("cp949")

    elif File_Ext == "docx":
        try:
            doc = Document(io.BytesIO(File_Bytes))
            text = "\n".join([para.text for para in doc.paragraphs])
            return text
        except Exception as e:
            if (
                "Package not found" in str(e)
                or "password" in str(e).lower()
                or "not a zip file" in str(e).lower()
            ):
                raise ValueError("[ERROR] DOCX 파싱 실패 : 암호로 보호된 DOCX 문서입니다.")
        raise ValueError("[ERROR] DOCX 파싱 실패")
    
    elif File_Ext == "pdf":
        try:
            with fitz.open(stream=File_Bytes, filetype="pdf") as doc:
                if doc.is_encrypted:
                    raise ValueError("암호로 보호된 PDF 문서입니다.")
                text = " ".join([page.get_text().replace("\n", " ") for page in doc])
                return text
        except RuntimeError as e:
            if "cannot decrypt" in str(e).lower() or "encrypted" in str(e).lower():
                raise ValueError("암호로 보호된 PDF 문서입니다.")
            raise ValueError(f"[ERROR] PDF 파싱 실패: {e}")
        except Exception as e:
            raise ValueError(f"[ERROR] PDF 파싱 실패: {e}")

def create_docx_report(detected_items: list) -> bytes:
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = '맑은 고딕'  # 또는 'HY헤드라인M', '바탕체' 등의 다른 폰트도 가능하다.
    font.size = Pt(12)
    style._element.rPr.rFonts.set(qn('w:eastAsia'), '맑은 고딕')  # 여기서 사용할 건 "맑은 고딕"

    doc.add_heading("탐지된 민감정보", 0)
    for item in detected_items:
        doc.add_paragraph(f"{item['type']}: {item['value']}")
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.read()

def create_pdf_report(detected_items: list) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    pdfmetrics.registerFont(UnicodeCIDFont('HYSMyeongJo-Medium'))
    textobject = c.beginText(50, 800)
    textobject.setFont("HYSMyeongJo-Medium", 12)
    textobject.textLine("탐지된 민감정보:")
    textobject.textLine("----------------------------")
    for item in detected_items:
        textobject.textLine(f"{item['type']}: {item['value']}")
    c.drawText(textobject)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()

def detect_by_regex(Text: str) -> list:
    Patterns = {
              "phone": re.compile(r"\b01[016789]-?\d{3,4}-?\d{4}\b"), # 전화번호
              "email": re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"), # 이메일 주소
              "birth": re.compile(r"\b(19|20)\d{2}[년./\- ]+(0?[1-9]|1[0-2])[월./\- ]+(0?[1-9]|[12][0-9]|3[01])[일]?\b"), # 생년월일
              "ssn": re.compile(r"\b\d{6}[-]?[1-4]\d{6}\b"),  # 주민등록번호
              "alien_reg": re.compile(r"\b\d{6}[-]?[5-8]\d{6}\b"), # 외국인등록번호
              "driver_license": re.compile(r"\d{2}-\d{2}-\d{6}-\d{2}"),  # 운전면허번호
              "passport": re.compile(r"[A-Z]\d{2,3}[A-Z]?\d{4,5}"), # 여권번호
              "account": re.compile(r"\b\d{6}[- ]?\d{2}[- ]?\d{6}\b"),  # 은행 계좌번호 - 국민은행
              "card": re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b"), #카드번호
              "zipcode": re.compile(r"\b\d{5}\b"), # 우편번호
              "ip": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b|\b([0-9a-fA-F]{0,4}:){1,7}[0-9a-fA-F]{0,4}\b")  # IPv4, IPv6
              }
    detected = []
    for label, pattern in Patterns.items():
        for match in pattern.finditer(Text):
            detected.append({
                "type": label,
                "value": match.group(),
                "span": match.span()
            })
    return detected

def detect_by_ner(Text: str) -> list:
    Results = ner_pipeline(Text)
    Detected = []
    for Entity in Results:
        Label = Entity['entity_group']
        Word = Entity['word']
        Start = Entity.get('start')
        End = Entity.get('end')
        if Start is None or End is None:
            continue
        if Label.upper() in ["PER", "PERSON", "NAME", "ORG", "ORGANIZATION", "DATE", "EMAIL", "SSN",
                             "CARD", "ID", "ACCOUNT", "PHONE", "NUMBER"]:
            Detected.append({"type": Label, "value": Word, "span": (Start, End)})
    return Detected


def apply_masking(original_text: str, detected: list) -> str:
    masked_text = list(original_text)
    length = len(masked_text)

    for item in detected:
        start, end = item.get("span", (None, None))

        # 값이 None이거나 잘못된 인덱스면 skip
        if start is None or end is None:
            continue
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if start < 0 or end > length or start >= end:
            continue
        if end > len(masked_text):  # 혹시 몰라 이중 방어
            continue

        try:
            masked_text[start:end] = "*" * (end - start)
        except IndexError as e:
            print(f"[WARNING] 마스킹 실패 (index error): {e} | span=({start}, {end})")
            continue

    return ''.join(masked_text)

def apply_face_mosaic(image_bytes: bytes) -> bytes:
    try:
        # 이미지 디코딩
        img_array = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        # Haar Cascade 로딩
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = face_cascade.detectMultiScale(img, scaleFactor=1.1, minNeighbors=5)

        for (x, y, w, h) in faces:
            roi = img[y:y+h, x:x+w]
            roi = cv2.resize(roi, (10, 10))  # 축소
            roi = cv2.resize(roi, (w, h))    # 확대
            img[y:y+h, x:x+w] = roi

        _, encoded_img = cv2.imencode(".jpg", img)
        return encoded_img.tobytes()

    except Exception as e:
        print(f"[ERROR] 얼굴 모자이크 실패: {e}")
        return image_bytes  # 실패 시 원본 반환

def encrypt_data(data: bytes, Key : bytes) -> bytes:
    try:
        Cipher = AES.new(Key, AES.MODE_CBC)
        CT_Bytes = Cipher.encrypt(pad(data, AES.block_size))
        return Cipher.iv + CT_Bytes
    except Exception as e:
        logging.error(f"암호화 실패: {e}", exc_info=True)
        return b''

def send_to_backend(encrypted_data: bytes, filename: str = "Detected_Info.txt") -> bool:
    url = "http://your-backend-api/upload"
    try:
        response = requests.post(url, files={"File": (filename, encrypted_data)})
        print(f"[INFO] 백엔드 응답 상태 코드: {response.status_code}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] 백엔드 전송 실패: {e}")
        return False
    
def handle_input_raw(Input_Data, Original_Format=None):
    if isinstance(Input_Data, bytes):
        print("[INFO] 파일 입력으로 감지됨")
        Parsed_Text = parse_file(Input_Data, Original_Format)
        Detected = detect_by_regex(Parsed_Text) + detect_by_ner(Parsed_Text)
        if not Detected:
            return None, None, "탐지된 민감정보 없음"

        Detected_Text = "\n".join(f"{d['type']}: {d['value']}" for d in Detected)
        masked_text = apply_masking(Parsed_Text, Detected)
        encrypted = encrypt_data(masked_text.encode("utf-8"), Key)
        backend_status = send_to_backend(encrypted, filename="Masked_Info.txt")

        if Original_Format == "pdf":
            file_bytes = create_pdf_report(Detected)
            media_type = "application/pdf"
        elif Original_Format == "docx":
            file_bytes = create_docx_report(Detected)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            file_bytes = Detected_Text.encode("utf-8")
            media_type = "text/plain"

        return Detected, file_bytes, media_type, masked_text, backend_status
    else:
        raise ValueError("지원하지 않는 입력 형식입니다.")