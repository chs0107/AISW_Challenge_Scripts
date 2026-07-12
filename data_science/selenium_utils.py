"""
Selenium 유틸리티. requests로 막히는 사이트(Cloudflare 등)에 사용.
webdriver-manager가 크롬드라이버를 자동 설치하므로 별도 다운로드 불필요.
(단, 이 컴퓨터에 Chrome 브라우저는 설치되어 있어야 함)
"""
import time
import random

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from crawler_utils import logger


def get_driver(headless: bool = True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,900")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def get_uc_driver(headless: bool = False, version_main: int = 149):
    """
    Cloudflare 등 강한 봇 차단이 있는 사이트용.
    일반 Selenium보다 자동화 흔적을 더 많이 지움.
    version_main은 설치된 Chrome 버전에 맞춰야 함 (다르면 SessionNotCreatedException 발생).
    """
    import undetected_chromedriver as uc

    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    return uc.Chrome(options=options, version_main=version_main)


def fetch_rendered_html(driver, url: str, wait_sec: float = 3.0) -> str:
    """페이지 접속 후 JS 렌더링 대기, 최종 HTML 반환"""
    logger.info(f"[Selenium] 요청: {url}")
    driver.get(url)
    time.sleep(wait_sec + random.uniform(0, 1.5))
    return driver.page_source


CHALLENGE_MARKERS = ["잠시만 기다리십시오", "Just a moment", "checking your browser", "확인 중"]


def fetch_with_challenge_wait(driver, url: str, max_wait: int = 40, poll_interval: int = 3) -> str:
    """
    Cloudflare 등 'JS 챌린지' 페이지가 뜨는 사이트용.
    <title>에서 차단 문구가 사라질 때까지 주기적으로 재확인 (최대 max_wait초).
    """
    logger.info(f"[Selenium] 요청(챌린지 대기 모드): {url}")
    driver.get(url)

    elapsed = 0
    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval
        title = driver.title
        if not any(marker in title for marker in CHALLENGE_MARKERS):
            logger.info(f"챌린지 통과로 보임 ({elapsed}초 소요), 콘텐츠 로딩 추가 대기")
            time.sleep(2.0)
            return driver.page_source
        logger.info(f"아직 챌린지 진행 중... ({elapsed}/{max_wait}초)")

    logger.warning(f"{max_wait}초 대기했지만 여전히 차단 상태로 보임: {url}")
    return driver.page_source
