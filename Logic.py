import io
import re
import requests
import logging
import numpy as np
import fitz
import easyocr
import zipfile
from PIL import Image
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from docx import Document

Key = b"1234567890abcdef"
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
NER_MODEL_NAME = "xlm-roberta-large-finetuned-conll03-english"
ner_tokenizer = AutoTokenizer.from_pretrained(NER_MODEL_NAME)
ner_model = AutoModelForTokenClassification.from_pretrained(NER_MODEL_NAME)
ner_pipeline = pipeline("ner", model=ner_model, tokenizer=ner_tokenizer, grouped_entities=True)
reader = easyocr.Reader(['ko', 'en'])

def parse_file(File_Bytes: bytes, File_Ext: str) -> str:
    File_Ext = File_Ext.lower()

    if File_Ext == "txt":
        try:
            return File_Bytes.decode("utf-8"), None
        except UnicodeDecodeError:
            return File_Bytes.decode("cp949"), None

    elif File_Ext == "docx":
        try:
            file_stream = io.BytesIO(File_Bytes)
            doc = Document(file_stream)
        except Exception:
            raise ValueError("[ERROR] DOCX 파싱 실패: Document 객체 생성 불가")
        try:
            text = "\n".join([para.text or "" for para in doc.paragraphs])
            if not text.strip():
                print("[INFO] 텍스트 없음 → OCR 실행")
                text = run_ocr_on_docx_images(File_Bytes)
                if not text.strip():
                    raise ValueError("[ERROR] OCR 텍스트 추출 실패, 빈 문자열 반환")
            return text, None
        except Exception as e:
            raise ValueError(f"[ERROR] DOCX 파싱 실패 (내용 추출 중 오류): {e}")

    elif File_Ext == "pdf":
        try:
            doc = fitz.open(stream=File_Bytes, filetype="pdf")
            if doc.is_encrypted:
                raise ValueError("[ERROR] PDF 파싱 실패 : 암호로 보호된 PDF 문서입니다.")
            text = " ".join([page.get_text().replace("\n", " ") for page in doc])
            if not any(char.isalnum() for char in text):
                print("[INFO] 텍스트 없음 → OCR 실행")
                text = run_ocr_on_pdf_images(File_Bytes)
                if not text.strip():
                    print("[ERROR] OCR 텍스트 추출 실패, 빈 문자열 반환")
                    return ""
            return text, None
        except Exception as e:
            if any(keyword in str(e).lower() for keyword in ["암호", "cannot open broken document", "not a pdf", "password"]):
                raise ValueError(str(e))
            raise ValueError("[ERROR] PDF 파싱 실패")

def run_ocr_on_docx_images(file_bytes):
    ocr_text = ""
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as docx_zip:
            image_files = [f for f in docx_zip.namelist() if f.startswith("word/media/")]
            for image_name in image_files:
                with docx_zip.open(image_name) as image_file:
                    image = Image.open(image_file)
                    result = reader.readtext(np.array(image))
                    for box in result:
                        ocr_text += box[1] + "\n"
    except Exception as e:
        print(f"[ERROR] DOCX 이미지 OCR 실패: {e}")
    return ocr_text.replace("\n", " ").replace(":", "").replace(",", "").strip()

def run_ocr_on_pdf_images(pdf_bytes: bytes) -> str:
    ocr_text = ""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for idx, page in enumerate(doc):
            pix = page.get_pixmap()
            img = Image.open(io.BytesIO(pix.tobytes("ppm")))
            try:
                result = reader.readtext(np.array(img))
                for box in result:
                    ocr_text += box[1] + "\n"
            except Exception as e:
                print(f"[ERROR] EasyOCR 실패 (페이지 {idx}): {e}")
    return ocr_text.replace("\n", " ").replace(":", "").replace(",", "").strip()

def detect_by_regex(Text: str) -> list:
    Patterns = {
        "phone": re.compile(r"\b01[016789]-?\d{3,4}-?\d{4}\b"),
        "email": re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"),
        "birth": re.compile(r"\b(19|20)\d{2}[년./\\\- ]+(0?[1-9]|1[0-2])[월./\\\- ]+(0?[1-9]|[12][0-9]|3[01])[일]?\b"),
        "ssn": re.compile(r"\b\d{6}[-]?[[1-4]\d{6}\b"),
        "alien_reg": re.compile(r"\b\d{6}[-]?[5-8]\d{6}\b"),
        "driver_license": re.compile(r"\d{2}-\d{2}-\d{6}-\d{2}"),
        "passport": re.compile(r"[A-Z]\d{2,3}[A-Z]?\d{4,5}"),
        "account": re.compile(r"\b\d{6}[- ]?\d{2}[- ]?\d{6}\b"),
        "card": re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b"),
        "zipcode": re.compile(r"\b\d{5}\b"),
        "ip": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b|\b([0-9a-fA-F]{0,4}:){1,7}[0-9a-fA-F]{0,4}\b")
    }
    detected = []
    for label, pattern in Patterns.items():
        for match in pattern.finditer(Text):
            detected.append({"type": label, "value": match.group(), "span": match.span()})
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
        if Label.upper() in ["PER", "ORG", "LOC", "MISC"]:
            Detected.append({"type": Label, "value": Word, "span": (Start, End)})
    return Detected

def apply_masking(original_text: str, detected: list) -> str:
    masked_text = list(original_text)
    length = len(masked_text)

    for item in detected:
        start, end = item.get("span", (None, None))
        if start is None or end is None:
            continue
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if start < 0 or end > length or start >= end:
            continue
        if end > len(masked_text):
            continue
        try:
            masked_text[start:end] = "*" * (end - start)
        except IndexError as e:
            print(f"[WARNING] 마스킹 실패 (index error): {e} | span=({start}, {end})")
            continue

    return ''.join(masked_text)

def encrypt_data(data: bytes, Key: bytes) -> bytes:
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
        Parsed_Text, _ = parse_file(Input_Data, Original_Format)
        Parsed_Text = Parsed_Text.strip()
        Detected = detect_by_regex(Parsed_Text) + detect_by_ner(Parsed_Text)
        if not Detected:
            return Detected, "", False
        masked_text = apply_masking(Parsed_Text, Detected)
        encrypted = encrypt_data(masked_text.encode("utf-8"), Key)
        backend_status = send_to_backend(encrypted, filename="Masked_Info.txt")
        return Detected, masked_text, backend_status
    else:
        raise ValueError("지원하지 않는 입력 형식입니다.")