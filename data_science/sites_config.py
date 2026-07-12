"""
크롤링 대상 8개 사이트 설정.

url: 목록 페이지 주소. 확인 안 된 건 None으로 비워둠 -> 채워 넣어야 함.
needs_selenium:
    True  -> requests로 막힐 가능성이 높다고 확인/추정됨 (Selenium 권장)
    False -> requests로 접근 가능할 것으로 확인/추정됨
    None  -> 아직 모름 (diagnose_site.py 실행해서 확인)
note: 참고사항, TODO 표시
"""

SITES = {
    # ---------------- 남초 ----------------
    "dcinside_korean_women": {
        "label": "디시인사이드 - 한국 여성 마이너 갤러리",
        "url": "https://gall.dcinside.com/mgallery/board/lists/?id=koreawomen",
        "needs_selenium": None,  # 확인 필요: 원격 테스트에서는 빈 페이지 반환됨 (로컬에서 재확인 필요)
        "note": "diagnose_site.py 실행 결과 확인 필요",
    },
    "etoland_hit": {
        "label": "이토랜드 - HIT인기",
        "url": "https://etoland.co.kr/hit/list",
        "needs_selenium": False,  # 확인됨: requests로 접근 성공
        "note": "접근 확인 완료. 페이지네이션 방식은 diagnose 실행 후 raw_html에서 확인 필요",
    },
    "dogdrip_hot": {
        "label": "개드립 - 인기글",
        "url": "https://www.dogdrip.net/dogdrip?sort_index=popular&page=1",
        "needs_selenium": True,  # 확인됨: 봇 차단으로 접근 실패
        "note": "확인됨: 봇 차단으로 접근 실패. Selenium 필요",
    },
    "fmkorea_hot": {
        "label": "에펨코리아 - 화제(포텐 터짐)",
        "url": "https://www.fmkorea.com/best2",
        "needs_selenium": None,
        "note": "robots.txt에서 자동 접근을 명시적으로 차단함. 진행 여부 판단 필요",
    },
    # ---------------- 여초 ----------------
    "theqoo_hot": {
        "label": "더쿠 - HOT 전체",
        "url": "https://theqoo.net/hot",
        "needs_selenium": True,  # 확인됨: requests/자동화 요청 시 봇 차단 발생
        "note": "확인됨: 봇 차단으로 접근 실패. Selenium 필수",
    },
    "womad_monthly_best": {
        "label": "워마드 - 월간베스트",
        "url": "https://womad.life/best/monthlybest/1",
        "needs_selenium": True,  # 확인됨: 봇 차단으로 접근 실패
        "note": "확인됨: 봇 차단으로 접근 실패. 로그인 필요 여부도 별도 확인 필요",
    },
    "newdic_hot": {
        "label": "뉴덕 - HOT",
        "url": "https://newduck.net/HOT",
        "needs_selenium": True,  # 확인됨: 봇 차단으로 접근 실패
        "note": "확인됨: 봇 차단으로 접근 실패. Selenium 필요",
    },
    "haeyeongal_100": {
        "label": "해연갤 - 전체글 모아보기(개념글100)",
        "url": "https://hygall.com/index.php?best=100&mid=ex_all",
        "needs_selenium": False,  # 확인됨: requests로 접근/구조 파악 완료
        "note": "확인 완료. XpressEngine 표준 게시판 테이블 구조. hygall_scraper.py 참고",
    },
}
