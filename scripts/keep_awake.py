"""
Streamlit Community Cloud 앱이 잠들지 않도록 실제로 브라우저로 방문해주는 스크립트.

왜 requests.get() 대신 Playwright(가짜 브라우저)를 쓰나요?
- requests.get()은 200 응답을 받아도 실제로는 정적인 HTML 껍데기만 받아오는 경우가 많아서
  파이썬 앱 자체는 깨어나지 않을 수 있습니다.
- 실제로 앱을 깨우려면 자바스크립트 실행 + 웹소켓 연결이 필요한데,
  이건 진짜 브라우저(또는 이걸 흉내내는 Playwright)로만 가능합니다.
"""

import os
import random
import time
from playwright.sync_api import sync_playwright

# GitHub Actions의 "env:" 부분에서 넘겨준 APP_URL 값을 읽어옵니다.
APP_URL = os.environ.get("APP_URL", "").strip()

# 0~30분(0~1800초) 사이 랜덤하게 대기합니다.
# 워크플로우 자체는 30분마다 시작되므로, 이 대기 시간을 더하면
# 결과적으로 방문 간격이 30분~60분 사이에서 랜덤하게 됩니다.
WAIT_SECONDS = random.randint(0, 30 * 60)


def wake_up_app(url: str) -> None:
    if not url or "여기에" in url:
        raise ValueError(
            "APP_URL이 설정되지 않았습니다. "
            "GitHub Actions 워크플로우 파일의 APP_URL 값을 실제 주소로 바꿔주세요."
        )

    print(f"[대기] {WAIT_SECONDS}초({WAIT_SECONDS // 60}분) 동안 기다린 뒤 방문합니다.")
    time.sleep(WAIT_SECONDS)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        print(f"[방문] {url} 페이지를 엽니다.")
        page.goto(url, wait_until="domcontentloaded", timeout=120_000)

        # 페이지가 완전히 로드될 시간을 좀 줍니다.
        page.wait_for_timeout(5000)

        # 앱이 잠들어 있으면 "Yes, get this app back up!" 버튼이 나타납니다.
        wake_button = page.get_by_role("button", name="Yes, get this app back up!")

        if wake_button.count() > 0:
            print("[깨우기] 앱이 잠들어 있었습니다. 깨우기 버튼을 클릭합니다.")
            wake_button.click()
            # 앱이 다시 켜질 때까지 잠시 기다립니다.
            page.wait_for_timeout(60_000)
            print("[완료] 앱을 깨웠습니다.")
        else:
            print("[정상] 앱이 이미 깨어 있는 상태입니다.")

        browser.close()


if __name__ == "__main__":
    wake_up_app(APP_URL)
