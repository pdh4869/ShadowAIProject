# 보내주신 코드 그대로 적용
import re

NAME_WHITELIST = {'홍길동'}

def detect_by_ner_updated(Text: str, ner_pipeline, KOREAN_SURNAMES, NAME_BLACKLIST) -> list:
    if not Text.strip():
        return []
    
    # 정규식으로 이름 추출 ("성명이무송" 패턴)
    name_pattern = re.compile(r'성명([가-힣]{2,4})(?:생년월일|주소|연락처|전화|이메일|E-Mail|휴대폰|생년)')
    name_match = name_pattern.search(Text)
    extracted_name = None
    if name_match:
        extracted_name = name_match.group(1)
        print(f"[INFO] ✓ 정규식으로 이름 추출: {extracted_name}")
    
    print(f"[DEBUG] NER 입력: {Text[:100]}")
    Results = ner_pipeline(Text)
    print(f"[DEBUG] NER 원본 결과: {Results}")
    
    Detected = []
    location_parts = []  # LC(주소) 병합용
    
    # 정규식으로 추출한 이름 먼저 추가
    if extracted_name:
        Detected.append({"type": "PS", "value": extracted_name, "span": (0, 0)})
        print(f"[INFO] ✓ 정규식 이름 탐지: {extracted_name}")
    
    # 화이트리스트 이름 탐지 (NER이 놓치는 흔한 이름)
    for whitelist_name in NAME_WHITELIST:
        if whitelist_name in Text and whitelist_name not in [d['value'] for d in Detected]:
            start_idx = Text.find(whitelist_name)
            Detected.append({"type": "PS", "value": whitelist_name, "span": (start_idx, start_idx + len(whitelist_name))})
            print(f"[INFO] ✓ 화이트리스트 이름 탐지 (PS): {whitelist_name}")
    
    for Entity in Results:
        Label = Entity['entity_group']
        Word = Entity['word']
        Start = Entity.get('start')
        End = Entity.get('end')
        
        # ## 접두사 제거 (BERT 토큰화 부산물)
        if Word.startswith('##'):
            Word = Word[2:]
        
        print(f"[DEBUG] 엔티티: Label={Label}, Word={Word}")
        
        if Start is None or End is None:
            continue
        
        if Label.upper() in ["PER", "PS", "ORG", "OG", "LC", "DT"]:
            # LC (주소) 병합 처리
            if Label.upper() == "LC":
                location_parts.append(Word.strip())
                continue
            
            # ORG/OG (조직명) 처리
            if Label.upper() in ["ORG", "OG"]:
                clean_org = Word.replace(" ", "").strip()
                if len(clean_org) >= 2:
                    # 조직명 분리: "삼성전자 개발팀" → "삼성전자", "개발팀"
                    org_split_keywords = ['팀', '부', '부서', '본부', '지점', '센터', '연구소']
                    split_orgs = []
                    
                    # 공백으로 분리 먼저 시도
                    if ' ' in Word:
                        parts = Word.split(' ', 1)
                        if len(parts) == 2:
                            split_orgs = [parts[0].strip(), parts[1].strip()]
                            print(f"[INFO] ⚠ 조직명 분리 (공백): '{Word}' → {split_orgs}")
                    
                    # 공백 없으면 키워드로 분리
                    if not split_orgs:
                        for keyword in org_split_keywords:
                            if keyword in Word and not Word.endswith(keyword):
                                idx = Word.find(keyword)
                                if idx > 0:
                                    part1 = Word[:idx].strip()
                                    part2 = Word[idx:].strip()
                                    if part1 and part2:
                                        split_orgs = [part1, part2]
                                        print(f"[INFO] ⚠ 조직명 분리 (키워드): '{Word}' → {split_orgs}")
                                        break
                    
                    if split_orgs:
                        for org in split_orgs:
                            if len(org.replace(" ", "")) >= 2:
                                Detected.append({"type": "ORG", "value": org, "span": (Start, End)})
                                print(f"[INFO] ✓ NER 탐지 (ORG 분리): {org}")
                    else:
                        Detected.append({"type": "ORG", "value": Word, "span": (Start, End)})
                        print(f"[INFO] ✓ NER 탐지 (ORG): {Word}")
                else:
                    print(f"[INFO] ✗ NER 필터링 (ORG): {Word} (너무 짧음)")
                continue
            
            # DT (날짜/숫자) - 학번/사번으로 처리
            if Label.upper() == "DT":
                # 숫자만 있고 8자리 이상이면 학번/사번으로 간주
                if Word.isdigit() and len(Word) >= 8:
                    Detected.append({"type": "student_id", "value": Word, "span": (Start, End)})
                    print(f"[INFO] ✓ NER 탐지 (student_id): {Word}")
                continue
            
            # PS (사람 이름) 필터링
            if Label.upper() in ["PS", "PER"]:
                # 특수문자 제거 (앞뒤만)
                Word = re.sub(r'^[^가-힣a-zA-Z]+', '', Word)
                Word = re.sub(r'[^가-힣a-zA-Z]+$', '', Word)
                Word = Word.strip()
                
                if not Word:
                    continue
                
                clean_word = Word.replace(" ", "").strip()
                
                # 한글 포함 여부 확인
                has_korean = any('\uac00' <= c <= '\ud7a3' for c in Word)
                if not has_korean:
                    print(f"[INFO] ✗ NER 필터링 ({Label}): {Word} (한글 없음)")
                    continue
                
                # 조직명 키워드 체크 (PS로 잘못 탐지된 경우)
                org_keywords = ['회사', '전자', '그룹', '기업', '주식회사', '(주)', '㈜', 
                               '학교', '대학교', '대학', '고등학교', '중학교', '초등학교',
                               '병원', '의원', '센터', '연구소', '재단', '협회', '은행',
                               '부서', '팀', '본부', '지점', '영업소']
                if any(keyword in Word for keyword in org_keywords):
                    print(f"[INFO] ✗ NER 필터링 ({Label}): {Word} (조직명 키워드) → ORG로 재분류")
                    Detected.append({"type": "ORG", "value": Word, "span": (Start, End)})
                    continue
                
                # 2글자 이하 제외
                if len(clean_word) <= 2:
                    print(f"[INFO] ✗ NER 필터링 ({Label}): {Word} (2글자 이하)")
                    continue
                
                # 숫자만 있는 경우 제외
                if clean_word.isdigit():
                    print(f"[INFO] ✗ NER 필터링 ({Label}): {Word} (숫자만 포함)")
                    continue
            
            Detected.append({"type": Label, "value": Word, "span": (Start, End)})
            print(f"[INFO] ✓ NER 탐지 ({Label}): {Word}")
    
    # 주소 개별 처리 (병합하지 않음)
    for loc in location_parts:
        if loc.strip():
            Detected.append({"type": "LC", "value": loc.strip(), "span": (0, 0)})
            print(f"[INFO] ✓ 주소 탐지: {loc.strip()}")
    
    return Detected
