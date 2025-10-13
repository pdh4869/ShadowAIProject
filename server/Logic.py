import io
import re
import logging
import numpy as np
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

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

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
            text = "\n".join([para.text or "" for para in doc.paragraphs])
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
            text = " ".join([page.get_text().replace("\n", " ") for page in doc])
            if not any(char.isalnum() for char in text):
                print("[INFO] 텍스트 없음 → OCR 실행")
                text = run_ocr_on_pdf_images(File_Bytes)
                if not text.strip():
                    print("[WARN] OCR 텍스트 추출 실패, 빈 문자열 반환")
            return text, False
        except Exception as e:
            raise ValueError(f"[ERROR] PDF 파싱 실패: {e}")
    
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

def run_ocr_on_docx_images(file_bytes):
    ocr_text = ""
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as docx_zip:
            image_files = [f for f in docx_zip.namelist() if f.startswith("word/media/")]
            print(f"[INFO] DOCX 내부 이미지 {len(image_files)}개 발견, OCR 시작")
            for image_name in image_files:
                with docx_zip.open(image_name) as image_file:
                    image = Image.open(image_file)
                    result = reader.readtext(np.array(image))
                    for box in result:
                        ocr_text += box[1] + "\n"
    except Exception as e:
        print(f"[ERROR] DOCX 이미지 OCR 실패: {e}")
    return ocr_text.strip()

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

# ==========================
# 정규식 탐지 (강화 - 띄어쓰기/하이픈 우회 방지)
# ==========================
def detect_by_regex(Text: str) -> list:
    """
    정규식 기반 개인정보 탐지 (우회 방지 강화)
    띄어쓰기, 하이픈 없이도 탐지 가능
    """
    # 탐지 전 텍스트 정규화 (공백/하이픈 제거한 버전도 함께 검사)
    normalized_text = re.sub(r'[\s\-]', '', Text)
    
    Patterns = {
        # 한글 이름 (2-4글자, NER fallback용)
        "korean_name": re.compile(r"\b[가-힣]{2,4}\b"),
        
        # 전화번호: 010-1234-5678, 01012345678, 010 1234 5678 모두 탐지
        "phone": re.compile(r"\b01[016789][\s\-]?\d{3,4}[\s\-]?\d{4}\b"),
        
        # 이메일
        "email": re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"),
        
        # 생년월일
        "birth": re.compile(r"\b(19|20)\d{2}[년./\- ]+(0?[1-9]|1[0-2])[월./\- ]+(0?[1-9]|[12][0-9]|3[01])[일]?\b"),
        
        # 주민등록번호: 123456-1234567, 1234561234567 모두 탐지
        "ssn": re.compile(r"\b\d{6}[\s\-]?[1-4]\d{6}\b"),
        
        # 외국인등록번호
        "alien_reg": re.compile(r"\b\d{6}[\s\-]?[5-8]\d{6}\b"),
        
        # 운전면허번호
        "driver_license": re.compile(r"\b\d{2}[\s\-]?\d{2}[\s\-]?\d{6}[\s\-]?\d{2}\b"),
        
        # 여권번호
        "passport": re.compile(r"\b[A-Z]\d{2,3}[A-Z]?\d{4,5}\b"),
        
        # 계좌번호
        "account": re.compile(r"\b\d{6}[\s\-]?\d{2}[\s\-]?\d{6}\b"),
        
        # 카드번호: 1234-5678-9012-3456, 1234567890123456 모두 탐지
        "card": re.compile(r"\b(?:\d{4}[\s\-]?){3}\d{4}\b"),
        
        # IP 주소
        "ip": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    }
    
    detected = []
    
    # 원본 텍스트에서 탐지
    for label, pattern in Patterns.items():
        for match in pattern.finditer(Text):
            detected.append({
                "type": label, 
                "value": match.group(), 
                "span": match.span()
            })
    
    # 정규화된 텍스트에서 추가 탐지 (공백/하이픈 우회 시도 차단)
    normalized_patterns = {
        # 전화번호 (공백/하이픈 없이)
        "phone_normalized": re.compile(r"\b01[016789]\d{7,8}\b"),
        
        # 주민등록번호 (공백/하이픈 없이)
        "ssn_normalized": re.compile(r"\b\d{6}[1-4]\d{6}\b"),
        
        # 외국인등록번호 (공백/하이픈 없이)
        "alien_reg_normalized": re.compile(r"\b\d{6}[5-8]\d{6}\b"),
        
        # 운전면허번호 (공백/하이픈 없이)
        "driver_license_normalized": re.compile(r"\b\d{2}\d{2}\d{6}\d{2}\b"),
        
        # 계좌번호 (공백/하이픈 없이)
        "account_normalized": re.compile(r"\b\d{6}\d{2}\d{6}\b"),
        
        # 카드번호 (공백/하이픈 없이)
        "card_normalized": re.compile(r"\b\d{16}\b")
    }
    
    # 정규화된 텍스트에서 탐지 (중복 제거)
    existing_values = {d["value"].replace(" ", "").replace("-", "") for d in detected}
    
    for label, pattern in normalized_patterns.items():
        original_label = label.replace("_normalized", "")
        for match in pattern.finditer(normalized_text):
            normalized_value = match.group()
            if normalized_value not in existing_values:
                # 원본 텍스트에서 해당 위치 찾기
                detected.append({
                    "type": original_label,
                    "value": normalized_value,
                    "span": match.span()
                })
                existing_values.add(normalized_value)
    
    return detected

# ==========================
# NER 탐지 (조직명 제외)
# ==========================
def detect_by_ner(Text: str) -> list:
    if not Text.strip():
        return []
    
    print(f"[DEBUG] NER 입력: {Text[:100]}")
    Results = ner_pipeline(Text)
    print(f"[DEBUG] NER 결과: {Results}")
    
    Detected = []
    for Entity in Results:
        Label = Entity['entity_group']
        Word = Entity['word']
        Start = Entity.get('start')
        End = Entity.get('end')
        
        print(f"[DEBUG] 엔티티: Label={Label}, Word={Word}")
        
        if Start is None or End is None:
            continue
        
        if Label.upper() in ["PER", "PS", "ORG", "LOC", "MISC"]:
            Detected.append({"type": Label, "value": Word, "span": (Start, End)})
            print(f"[INFO] ✓ NER 탐지 ({Label}): {Word}")
    
    return Detected

# ==========================
# 얼굴 탐지 (MTCNN)
# ==========================
def detect_faces_in_image_bytes(image_bytes):
    """이미지에서 얼굴을 탐지합니다"""
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_np = np.array(img)
        results = detector.detect_faces(img_np)
        detections = []
        for res in results:
            x, y, w, h = res['box']
            detections.append({
                "bbox": [int(x), int(y), int(w), int(h)], 
                "confidence": float(res['confidence'])
            })
        if len(detections) > 0:
            print(f"[INFO] ✓ MTCNN 얼굴 탐지 성공: {len(detections)}개 발견")
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

def detect_images_in_pdf(pdf_bytes):
    results = []
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            for pno, page in enumerate(doc):
                images = page.get_images(full=True)
                if len(images) > 0:
                    print(f"[INFO] PDF 페이지 {pno+1}에서 이미지 {len(images)}개 발견")
                for img_index, img in enumerate(images):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    img_bytes = base_image.get("image")
                    if img_bytes:
                        faces = detect_faces_in_image_bytes(img_bytes)
                        if len(faces) > 0:
                            print(f"[INFO] ✓ PDF p{pno+1}, img{img_index} → 얼굴 {len(faces)}개 탐지")
                            results.append({
                                "page": pno + 1,
                                "image_index": img_index,
                                "faces_found": len(faces),
                                "faces": faces
                            })
    except Exception as e:
        print(f"[WARN] PDF 이미지 검사 실패: {e}")
    return results

def scan_file_for_face_images(file_bytes, file_ext):
    """파일 내 이미지에서 얼굴을 탐지합니다"""
    file_ext = file_ext.lower()
    print(f"[INFO] === 얼굴 이미지 스캔 시작 ({file_ext}) ===")
    
    if file_ext == "docx":
        return detect_images_in_docx(file_bytes)
    elif file_ext == "pdf":
        return detect_images_in_pdf(file_bytes)
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
        print(f"[INFO] 텍스트 분석 중... (길이: {len(Parsed_Text)} 글자)")
        
        # NER 먼저 실행
        ner_results = detect_by_ner(Parsed_Text)
        
        # 정규식 실행
        regex_results = detect_by_regex(Parsed_Text)
        
        # NER로 탐지된 이름 목록
        ner_names = {d["value"] for d in ner_results if d["type"].upper() in ["PER", "PS"]}
        
        # 정규식에서 korean_name 중복 제거
        filtered_regex = [d for d in regex_results if not (d["type"] == "korean_name" and d["value"] in ner_names)]
        
        Detected = filtered_regex + ner_results
        
        if len(Detected) > 0:
            print(f"[INFO] ✓ 텍스트 개인정보 {len(Detected)}개 탐지")
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