#!/usr/bin/env python3
"""수원 샘내마을 5개 단지 아파트 매매 실거래가 수집 스크립트.

국토교통부 아파트 매매 실거래가 API(공공데이터포털)를 호출해
장안구(41111) 데이터 중 샘내마을 5개 단지만 걸러 data/data.json 으로 저장한다.

사용법:
  SERVICE_KEY=발급받은키 python scripts/fetch_data.py          # 데이터 수집
  SERVICE_KEY=발급받은키 python scripts/fetch_data.py --list   # 단지명 탐색(검증용)
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone, timedelta

API_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
RENT_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"
LAWD_CD = "41111"          # 수원시 장안구
START_YM = "202101"        # 수집 시작 연월
DONGS = {"정자동", "율전동", "천천동"}  # 샘내마을 일대 법정동

# 단지명 매핑: (우선순위 순서대로) 키워드 → 표시명
NAME_RULES = [
    (("신명",), "신명스카이뷰"),
    (("일성",), "수원일성"),
    (("진덕", "삼호"), "삼호진덕"),
    (("한일", "신안"), "한일신안"),
    (("현대",), "현대"),
]

KST = timezone(timedelta(hours=9))


def month_range(start_ym: str):
    y, m = int(start_ym[:4]), int(start_ym[4:])
    today = datetime.now(KST).date()
    while (y, m) <= (today.year, today.month):
        yield f"{y}{m:02d}"
        m += 1
        if m > 12:
            y, m = y + 1, 1


def fetch_month(service_key: str, ymd: str, url: str = API_URL):
    """한 달치 항목(dict 리스트) 반환. 페이지네이션 처리."""
    items, page = [], 1
    while True:
        params = {
            "serviceKey": service_key,
            "LAWD_CD": LAWD_CD,
            "DEAL_YMD": ymd,
            "pageNo": str(page),
            "numOfRows": "1000",
        }
        full = url + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(full, timeout=30) as res:
            body = res.read().decode("utf-8")
        root = ET.fromstring(body)
        code = root.findtext(".//resultCode", "")
        if code not in ("00", "000"):
            msg = root.findtext(".//resultMsg", "unknown")
            raise RuntimeError(f"{ymd} API 오류 [{code}] {msg}")
        page_items = root.findall(".//item")
        for it in page_items:
            items.append({c.tag: (c.text or "").strip() for c in it})
        total = int(root.findtext(".//totalCount", "0"))
        if page * 1000 >= total:
            return items
        page += 1


def get(d, *keys):
    """신/구 API 태그명 호환 조회."""
    for k in keys:
        if k in d and d[k]:
            return d[k]
    return ""


def display_name(apt_nm: str):
    for keywords, name in NAME_RULES:
        if any(k in apt_nm for k in keywords):
            return name
    return None


def base_fields(raw):
    """매매/전월세 공통 필드 추출. 필터 통과 못 하면 None."""
    dong = get(raw, "umdNm", "법정동")
    apt = get(raw, "aptNm", "아파트")
    if dong not in DONGS:
        return None
    name = display_name(apt)
    if name is None:
        return None
    return {
        "apt": name,
        "rawApt": apt,
        "dong": dong,
        "date": "{}-{:02d}-{:02d}".format(
            get(raw, "dealYear", "년"),
            int(get(raw, "dealMonth", "월")),
            int(get(raw, "dealDay", "일")),
        ),
        "area": float(get(raw, "excluUseAr", "전용면적")),
        "floor": int(get(raw, "floor", "층") or 0),
    }


def to_int(s):
    return int(s.replace(",", "")) if s.strip() else 0


def main():
    service_key = os.environ.get("SERVICE_KEY", "")
    if not service_key:
        sys.exit("환경변수 SERVICE_KEY 가 필요합니다.")
    list_mode = "--list" in sys.argv

    seen_names = set()
    sales, rents = [], []
    rent_ok = True
    for ymd in month_range(START_YM):
        # 매매
        for raw in fetch_month(service_key, ymd, API_URL):
            dong = get(raw, "umdNm", "법정동")
            apt = get(raw, "aptNm", "아파트")
            if dong in DONGS:
                seen_names.add(f"{dong} | {apt}")
            base = base_fields(raw)
            if base is None:
                continue
            if get(raw, "cdealType", "해제여부") == "O":  # 해제된 거래 제외
                continue
            base["price"] = to_int(get(raw, "dealAmount", "거래금액"))  # 만원
            base["buildYear"] = int(get(raw, "buildYear", "건축년도") or 0)
            sales.append(base)
        # 전월세 (활용신청 전이면 건너뜀)
        if rent_ok:
            try:
                for raw in fetch_month(service_key, ymd, RENT_URL):
                    base = base_fields(raw)
                    if base is None:
                        continue
                    base["deposit"] = to_int(get(raw, "deposit", "보증금액"))    # 만원
                    base["rent"] = to_int(get(raw, "monthlyRent", "월세금액"))  # 만원, 0이면 전세
                    rents.append(base)
            except Exception as e:
                rent_ok = False
                print(f"[경고] 전월세 API 사용 불가, 매매만 수집합니다: {e}", file=sys.stderr)
        time.sleep(0.2)  # 호출 간격
        print(f"{ymd} 완료 (매매 {len(sales)} / 전월세 {len(rents)})", file=sys.stderr)

    if list_mode:
        print("\n[탐색] 대상 법정동에서 발견된 단지명:")
        for n in sorted(seen_names):
            print(" ", n)
        return

    sales.sort(key=lambda t: t["date"])
    rents.sort(key=lambda t: t["date"])
    out = {
        "updated": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "sample": False,
        "sales": sales,
        "rents": rents,
    }
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"저장 완료: 매매 {len(sales)} / 전월세 {len(rents)} → data/data.json", file=sys.stderr)


if __name__ == "__main__":
    main()
