# HuggingFace 토큰 설정 가이드

이 문서는 **한국어 NER(Named Entity Recognition) 모델**을 사용하기 위한 HuggingFace 토큰 설정 방법을 설명합니다.

---

## 📋 목차
1. [HuggingFace 토큰이 필요한 이유](#1-huggingface-토큰이-필요한-이유)
2. [HuggingFace 계정 생성](#2-huggingface-계정-생성)
3. [액세스 토큰 발급](#3-액세스-토큰-발급)
4. [환경 변수 설정 (Windows)](#4-환경-변수-설정-windows)
5. [환경 변수 설정 (PowerShell)](#5-환경-변수-설정-powershell)
6. [환경 변수 설정 (CMD)](#6-환경-변수-설정-cmd)
7. [설정 확인](#7-설정-확인)
8. [문제 해결](#8-문제-해결)

---

## 1. HuggingFace 토큰이 필요한 이유

본 프로젝트는 **한국어 인명 탐지**를 위해 다음 NER 모델을 사용합니다:
- 모델명: `soddokayo/klue-roberta-base-ner`
- 용도: 한국어 텍스트에서 인명(PS), 조직명(ORG), 주소(LC) 등을 자동 탐지

일부 HuggingFace 모델은 **인증이 필요**하며, 토큰 없이도 작동할 수 있지만 **토큰이 있으면 더 안정적**입니다.

---

## 2. HuggingFace 계정 생성

### 2-1. 회원가입
1. 브라우저에서 https://huggingface.co 접속
2. 우측 상단 **Sign Up** 클릭
3. 다음 정보 입력:
   - **Email**: 본인 이메일 주소
   - **Username**: 사용자명 (영문/숫자)
   - **Password**: 비밀번호 (8자 이상)
4. **Create Account** 클릭
5. 이메일 인증 링크 클릭하여 계정 활성화

### 2-2. 로그인
- 계정 생성 후 https://huggingface.co/login 에서 로그인

---

## 3. 액세스 토큰 발급

### 3-1. 토큰 생성 페이지 이동
1. 로그인 후 우측 상단 **프로필 아이콘** 클릭
2. **Settings** 선택
3. 좌측 메뉴에서 **Access Tokens** 클릭
   - 직접 링크: https://huggingface.co/settings/tokens

### 3-2. 새 토큰 생성
1. **New token** 버튼 클릭
2. 토큰 정보 입력:
   - **Name**: `PII_Detection_Project` (원하는 이름)
   - **Role**: **Read** 선택 (읽기 권한만 필요)
3. **Generate a token** 클릭

### 3-3. 토큰 복사
- 생성된 토큰이 화면에 표시됩니다
- 예시: `hf_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890`
- **⚠️ 중요**: 이 토큰은 **한 번만 표시**되므로 반드시 복사해두세요!
- 복사 후 안전한 곳에 저장 (메모장, 비밀번호 관리자 등)

---

## 4. 환경 변수 설정 (Windows)

### 방법 1: 시스템 환경 변수 (영구 설정 - 권장)

#### 4-1. 시스템 속성 열기
1. **Windows 키 + R** 눌러 실행 창 열기
2. `sysdm.cpl` 입력 후 **Enter**
3. **고급** 탭 선택
4. **환경 변수** 버튼 클릭

#### 4-2. 환경 변수 추가
1. **사용자 변수** 섹션에서 **새로 만들기** 클릭
2. 변수 정보 입력:
   - **변수 이름**: `HF_TOKEN`
   - **변수 값**: 복사한 토큰 (예: `hf_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890`)
3. **확인** 클릭
4. 모든 창에서 **확인** 클릭하여 저장

#### 4-3. 적용 확인
- **모든 터미널/CMD/PowerShell 창을 닫고 재시작**해야 적용됩니다
- 재부팅 후에도 유지됩니다

---

## 5. 환경 변수 설정 (PowerShell)

### 방법 2: PowerShell 명령어 (영구 설정)

#### 5-1. PowerShell 관리자 권한으로 실행
1. **Windows 키** 누르고 `PowerShell` 검색
2. **Windows PowerShell** 우클릭
3. **관리자 권한으로 실행** 선택

#### 5-2. 환경 변수 설정 명령어 실행
```powershell
# 사용자 환경 변수에 HF_TOKEN 추가 (영구 설정)
[System.Environment]::SetEnvironmentVariable('HF_TOKEN', 'hf_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890', 'User')
```

**⚠️ 주의**: `hf_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890` 부분을 **본인의 실제 토큰**으로 교체하세요!

#### 5-3. 현재 세션에 즉시 적용 (선택사항)
```powershell
# 현재 PowerShell 세션에만 적용 (임시)
$env:HF_TOKEN = "hf_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890"
```

#### 5-4. 확인
```powershell
# 환경 변수 확인
echo $env:HF_TOKEN
```

---

## 6. 환경 변수 설정 (CMD)

### 방법 3: CMD 명령어 (임시 설정)

#### 6-1. CMD 실행
1. **Windows 키 + R** 눌러 실행 창 열기
2. `cmd` 입력 후 **Enter**

#### 6-2. 현재 세션에만 적용 (임시)
```cmd
set HF_TOKEN=hf_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890
```

**⚠️ 주의**: 
- 이 방법은 **현재 CMD 창에만 적용**됩니다
- CMD 창을 닫으면 사라집니다
- **영구 설정이 필요하면 방법 1 또는 방법 2 사용**

#### 6-3. 영구 설정 (CMD에서 레지스트리 수정)
```cmd
setx HF_TOKEN "hf_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890"
```

- `setx` 명령어는 **영구 설정**
- 현재 CMD 창에는 적용 안 됨 (새 CMD 창에서 적용)

---

## 7. 설정 확인

### 7-1. 환경 변수 확인

#### PowerShell에서 확인
```powershell
echo $env:HF_TOKEN
```

#### CMD에서 확인
```cmd
echo %HF_TOKEN%
```

#### Python에서 확인
```python
import os
print(os.getenv("HF_TOKEN"))
```

**정상 출력 예시**:
```
hf_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890
```

### 7-2. 서버 실행 테스트
```bash
cd server
python LocalServer_Final.py
```

**정상 로그 예시**:
```
[INFO] NER 모델 로딩 중: soddokayo/klue-roberta-base-ner
[INFO] ✓ 허깅페이스 토큰 인증 완료
[INFO] ✓ NER 모델 로딩 완료
```

---

## 8. 문제 해결

### 문제 1: "HF_TOKEN 환경 변수 없음" 경고
**증상**:
```
[WARN] HF_TOKEN 환경 변수 없음 - 공개 모델로 시도
```

**해결**:
1. 환경 변수가 제대로 설정되었는지 확인
2. **모든 터미널/CMD/PowerShell 창을 닫고 재시작**
3. 필요시 컴퓨터 재부팅

### 문제 2: 토큰 인증 실패
**증상**:
```
[ERROR] 401 Unauthorized
```

**해결**:
1. 토큰이 올바른지 확인 (복사 시 공백 포함 여부)
2. HuggingFace에서 토큰이 활성화되어 있는지 확인
3. 토큰 권한이 **Read**인지 확인

### 문제 3: 모델 다운로드 실패
**증상**:
```
[ERROR] Connection timeout
```

**해결**:
1. 인터넷 연결 확인
2. 방화벽/프록시 설정 확인
3. HuggingFace 서버 상태 확인: https://status.huggingface.co

### 문제 4: 환경 변수가 적용 안 됨
**해결**:
1. **모든 터미널 창 닫기**
2. 새 터미널 열기
3. 여전히 안 되면 **컴퓨터 재부팅**
4. 시스템 환경 변수 설정 재확인

---

## 9. 보안 주의사항

### ⚠️ 토큰 보안
- **절대 GitHub, 공개 저장소에 업로드하지 마세요**
- **코드에 직접 하드코딩하지 마세요**
- 환경 변수로만 관리하세요
- 토큰이 유출되면 즉시 HuggingFace에서 삭제하고 재발급하세요

### 토큰 삭제 방법
1. https://huggingface.co/settings/tokens 접속
2. 해당 토큰 옆 **Manage** 클릭
3. **Delete** 클릭

---

## 10. 추가 정보

### 토큰 없이 사용 가능한가?
- **가능합니다**
- 공개 모델은 토큰 없이도 다운로드 가능
- 단, 토큰이 있으면 더 안정적이고 속도 제한이 완화됩니다

### 토큰 유효기간
- **무기한** (삭제하지 않는 한 계속 사용 가능)
- 보안상 주기적으로 재발급 권장 (6개월~1년)

### 여러 프로젝트에서 같은 토큰 사용 가능?
- **가능합니다**
- 하나의 토큰을 여러 프로젝트에서 공유 가능
- 프로젝트별로 다른 토큰을 발급해도 됩니다

---

## 11. 요약 (빠른 설정)

### Windows 빠른 설정 (PowerShell)
```powershell
# 1. HuggingFace에서 토큰 발급
# 2. PowerShell 관리자 권한으로 실행
# 3. 아래 명령어 실행 (토큰 교체 필수!)

[System.Environment]::SetEnvironmentVariable('HF_TOKEN', '여기에_본인_토큰_입력', 'User')

# 4. 모든 터미널 닫고 재시작
# 5. 확인
echo $env:HF_TOKEN
```

### 서버 실행
```bash
cd server
python LocalServer_Final.py
```

---

## 12. 참고 링크

- HuggingFace 공식 사이트: https://huggingface.co
- 토큰 관리 페이지: https://huggingface.co/settings/tokens
- 사용 모델: https://huggingface.co/soddokayo/klue-roberta-base-ner
- HuggingFace 문서: https://huggingface.co/docs

---

**작성일**: 2025년 1월  
**버전**: 1.0  
**프로젝트**: PII Detection Agent
