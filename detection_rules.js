// detection_rules.js
// 확장 탐지 항목: 전화, 이메일, 주민번호, 카드(Luhn), 계좌, 사업자, 우편번호, 생년월일, IP 주소

const PII_RULES = [
  { id: "PHONE", name: "전화번호", re: /\b(0\d{1,2})[-.\s]?\d{3,4}[-.\s]?\d{4}\b/g },
  { id: "EMAIL", name: "이메일", re: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g },
  { id: "RRN", name: "주민등록번호(추정)", re: /\b\d{6}-[1-8]\d{6}\b/g },
  { id: "BIRTHDATE", name: "생년월일", re: /\b(19|20)\d{2}[-./](0[1-9]|1[0-2])[-./](0[1-9]|[12]\d|3[01])\b/g },
  { id: "BIRTHDATE2", name: "생년월일(짧은형)", re: /\b\d{6}\b/g },
  { id: "POSTAL", name: "우편번호", re: /\b\d{5}\b/g },
  { id: "BIZ_REG", name: "사업자등록번호", re: /\b\d{3}-?\d{2}-?\d{5}\b/g },
  { id: "BANK_ACC", name: "계좌번호", re: /\b\d{2,4}[-\s]?\d{2,4}[-\s]?\d{4,10}\b/g },
  { id: "CARD_RAW", name: "카드번호(추정)", re: /\b(?:\d[ -]*?){13,19}\b/g },
  { id: "IPV4", name: "IP주소(IPv4)", re: /\b((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)\b/g },
  { id: "IPV6", name: "IP주소(IPv6)", re: /\b([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}\b/g }
];

// Luhn 검증
function luhnCheck(numStr) {
  const s = numStr.replace(/\D/g, '');
  let sum = 0, alt = false;
  for (let i = s.length - 1; i >= 0; i--) {
    let n = parseInt(s.charAt(i), 10);
    if (alt) { n *= 2; if (n > 9) n -= 9; }
    sum += n; alt = !alt;
  }
  return (s.length >= 13 && s.length <= 19) && (sum % 10 === 0);
}

// 사업자등록번호 검증
function validateBizReg(num) {
  const s = num.replace(/\D/g, '');
  if (s.length !== 10) return false;
  const weight = [1,3,7,1,3,7,1,3,5];
  let sum = 0;
  for (let i=0;i<9;i++) sum += parseInt(s[i],10) * weight[i];
  sum += Math.floor((parseInt(s[8],10) * 5) / 10);
  const check = (10 - (sum % 10)) % 10;
  return check === parseInt(s[9],10);
}

// 짧은 생년월일 필터
function seemsLikeShortBirth(s) {
  if (!/^\d{6}$/.test(s)) return false;
  const mm = parseInt(s.slice(2,4),10);
  const dd = parseInt(s.slice(4,6),10);
  if (mm < 1 || mm > 12) return false;
  if (dd < 1 || dd > 31) return false;
  return true;
}

function scanTextForPII(text) {
  const findings = [];
  if (!text || typeof text !== "string") return findings;

  for (const rule of PII_RULES) {
    let m;
    while ((m = rule.re.exec(text)) !== null) {
      const example = m[0]; const index = m.index;
      if (rule.id === "CARD_RAW") {
        const digits = example.replace(/\D/g,'');
        if (!luhnCheck(digits)) continue;
        findings.push({ kind: "카드번호", id: "CARD", example, index });
      } else if (rule.id === "BIZ_REG") {
        if (!validateBizReg(example)) continue;
        findings.push({ kind: "사업자등록번호", id: rule.id, example, index });
      } else if (rule.id === "BIRTHDATE2") {
        if (!seemsLikeShortBirth(example)) continue;
        findings.push({ kind: "생년월일(짧은형)", id: rule.id, example, index });
      } else {
        findings.push({ kind: rule.name, id: rule.id, example, index });
      }
    }
  }
  return findings;
}

window.scanTextForPII = scanTextForPII;
