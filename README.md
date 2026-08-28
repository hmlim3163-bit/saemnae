# 샘내마을 실거래가

수원 장안구 샘내마을 5개 단지(한일신안·삼호진덕·현대·신명스카이뷰·수원일성)의
국토교통부 매매·전세·월세 실거래가를 보여주는 정적 사이트입니다.
오름폭·신고가 뱃지, 전세가율·갭, 월별 거래량 차트를 제공합니다.
비용 0원: GitHub Pages(호스팅) + GitHub Actions(매일 자동 갱신).

## 배포 절차 (약 10분)

### 1. API 키 발급
1. [공공데이터포털](https://www.data.go.kr) 가입(개인회원이면 충분) → 로그인
2. 아래 **두 개** 모두 활용신청:
   - **국토교통부_아파트 매매 실거래가 자료**
   - **국토교통부_아파트 전월세 실거래가 자료**
3. 마이페이지에서 **일반 인증키(Decoding)** 복사 (두 API에 같은 키 사용)

※ 전월세 API를 신청하지 않아도 스크립트는 매매만 수집하고 넘어갑니다.

### 2. GitHub 저장소 만들기
1. github.com 에서 새 저장소 생성 (Public)
2. 이 폴더의 파일 전체를 업로드 (Add file → Upload files)

### 3. API 키 등록
저장소 → Settings → Secrets and variables → Actions → **New repository secret**
- Name: `SERVICE_KEY`
- Secret: 복사한 인증키 붙여넣기

### 4. 첫 데이터 수집
저장소 → Actions 탭 → "실거래가 데이터 갱신" → **Run workflow** 클릭
(2~3분 후 `data/data.json` 이 커밋되면 성공. 이후 매일 오전 6시 자동 갱신)

### 5. 사이트 공개
저장소 → Settings → Pages → Source: **Deploy from a branch**, Branch: `main` / root → Save
몇 분 후 `https://아이디.github.io/저장소명/` 으로 접속 가능

## 단지명 검증 (권장, 1회)

API상 단지명이 지도 표기와 다를 수 있습니다. 로컬에서 아래를 실행해
정자동·율전동·천천동에 등록된 실제 단지명을 확인하세요.

```
SERVICE_KEY=발급키 python scripts/fetch_data.py --list
```

출력된 이름이 5개 단지와 다르게 매칭되면 `scripts/fetch_data.py` 상단의
`NAME_RULES` 키워드를 수정하면 됩니다.

## 참고
- 해제된 거래는 자동 제외됩니다.
- 실거래 신고는 계약 후 30일 이내라 최신 거래는 늦게 반영될 수 있습니다.
- `data/data.json` 이 없거나 비어 있으면 사이트는 "샘플 데이터" 배지와 함께 가상 데이터를 표시합니다.
