from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as Ec
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
import time
import requests
import os
import random
import cv2
import numpy as np
import undetected_chromedriver as uc


class Code():
    '''
    滑动验证码破解
    '''

    def __init__(self, slider_ele=None, background_ele=None, count=1, save_image=False):
        '''

        :param slider_ele:
        :param background_ele:
        :param count:  验证重试次数
        :param save_image:  是否保存验证中产生的图片， 默认 不保存
        '''

        self.count = count
        self.save_images = save_image
        self.slider_ele = slider_ele
        self.background_ele = background_ele

    # 计算出滑动轨迹
    def get_slide_locus(self, distance):
        distance += 8
        v = 0
        m = 0.3
        # 保存0.3内的位移
        tracks = []
        current = 0
        mid = distance * 4 / 5
        while current <= distance:
            if current < mid:
                a = 2
            else:
                a = -3
            v0 = v
            s = v0 * m + 0.5 * a * (m ** 2)
            current += s
            tracks.append(round(s))
            v = v0 + a * m
        # 由于计算机计算的误差，导致模拟人类行为时，会出现分布移动总和大于真实距离，这里就把这个差添加到tracks中，也就是最后进行一步左移。
        # tracks.append(-(sum(tracks) - distance * 0.5))
        # tracks.append(10)
        return tracks

    def slide_verification(self, driver, slide_element, distance):
        '''

        :param driver: driver对象
        :param slide_element: 滑块元祖
        :type   webelement
        :param distance: 滑动距离
        :type: int
        :return:
        '''
        # 获取滑动前页面的url网址
        start_url = driver.current_url


        # 根据滑动的距离生成滑动轨迹
        locus = self.get_slide_locus(distance)

        print('生成的滑动轨迹为:{},轨迹的距离之和为{}'.format(locus, distance))

        # 按下鼠标左键
        ActionChains(driver).click_and_hold(slide_element).perform()

        time.sleep(0.5)

        # 遍历轨迹进行滑动
        for loc in locus:
            time.sleep(0.01)
            # 此处记得修改scrapy的源码 selenium\webdriver\common\actions\pointer_input.py中将DEFAULT_MOVE_DURATION改为50，否则滑动很慢
            ActionChains(driver).move_by_offset(loc, random.randint(-5, 5)).perform()
            ActionChains(driver).context_click(slide_element)

        # 释放鼠标
        ActionChains(driver).release(on_element=slide_element).perform()

        # # 判断是否通过验证，未通过下重新验证
        # time.sleep(2)
        # # 滑动之后的yurl链接
        # end_url = driver.current_url

        # if start_url == end_url and self.count > 0:
        #     print('第{}次验证失败，开启重试'.format(6 - self.count))
        #     self.count -= 1
        #     self.slide_verification(driver, slide_element, distance)

    def onload_save_img(self, url, filename="image.png"):
        '''
        下载图片并保存
        :param url: 图片网址
        :param filename: 图片名称
        :return:
        '''
        try:
            response = requests.get(url)
        except Exception as e:
            print('图片下载失败')
            raise e
        else:
            with open(filename, 'wb') as f:
                f.write(response.content)

    def image_crop(self, image, loc):
        cv2.rectangle(image, loc[0], loc[1], (7, 249, 151), 2)
        cv2.imshow('Show', image)
        # cv2.imshow('Show2', slider_pic)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


class Login(object):
    def __init__(self, user, password, retry):
        # self.display = Display(visible=0, size=(800, 800))
        # self.display.start()
        # 创建一个参数对象，用来控制chrome以无界面模式打开
        chrome_options = webdriver.ChromeOptions()
        # chrome_options.add_argument('--headless')  # # 浏览器不提供可视化页面
        chrome_options.add_argument('--disable-gpu')  # 禁用GPU加速,GPU加速可能会导致Chrome出现黑屏，且CPU占用率高达80%以上
        # chrome_options.add_argument('--no-sandbox')
        # chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-dev-shm-usage')

        self.browser = uc.Chrome()  # chrome实例化会自动下载chromedriver - 最新版本
        self.wait = WebDriverWait(self.browser, 20)
        self.url = 'https://www.zhihu.com/signin'
        self.sli = Code()
        self.user = user
        self.password = password
        self.retry = retry  # 重试次数

    def login(self):
        # 请求网址，登陆操作
        self.browser.get(self.url)
        login_element = self.browser.find_element(By.XPATH,
                                                  '//*[@id="root"]/div/main/div/div/div/div/div[2]/div/div[1]/div/div[1]/form/div[1]/div[2]')

        self.browser.execute_script("arguments[0].click();", login_element)
        time.sleep(5)

        # 输入账号
        username = self.wait.until(
            # 查询输入账号的框
            Ec.element_to_be_clickable((By.CSS_SELECTOR, '.SignFlow-account input'))
        )
        username.send_keys(self.user)
        # 输入密码
        password = self.wait.until(
            Ec.element_to_be_clickable((By.CSS_SELECTOR, '.SignFlow-password input'))
        )
        password.send_keys(self.password)

        # 登录框
        submit = self.wait.until(
            Ec.element_to_be_clickable((By.CSS_SELECTOR, '.Button.SignFlow-submitButton'))
        )

        time.sleep(3)
        submit.click()
        time.sleep(3)

        k = 1
        # while True:
        while k < self.retry:
            # 获取图片并进行下载
            bg_img = self.wait.until(
                Ec.presence_of_element_located((By.CSS_SELECTOR, '.yidun_bgimg .yidun_bg-img'))
            )

            background_url = bg_img.get_attribute('src')
            background = "background.jpg"
            # download the pic
            time.sleep(3)
            self.sli.onload_save_img(background_url, background)

            # 获取验证码滑动距离
            baidu = BaiduLogin("RO00QIMixnXaGmpxgzrrKv3H", "z7Rzjo3iPungqlvGXNS4jZoCNj0KTUsx")
            # distance从API返回，可能返回时间较长，需要等待一
            distance = baidu.recognize(baidu.get_access_token(), background)
            print('滑动距离是', distance)

            time.sleep(2)
            # 初始位置在左边靠右一点
            distance = distance - 4
            print('实际滑动距离是', distance)

            # 滑块对象
            element = self.browser.find_element(By.CSS_SELECTOR,
                                                '.yidun_slider')
            # 滑动函数
            self.sli.slide_verification(self.browser, element, distance)

            # 滑动之后的url链接
            time.sleep(5)
            # 登录框
            try:
                submit = self.wait.until(
                    Ec.element_to_be_clickable((By.CSS_SELECTOR, '.Button.SignFlow-submitButton'))
                )
                submit.click()
                time.sleep(3)
            except:
                pass

            end_url = self.browser.current_url
            print(end_url)

            # 登陆成功的判断，正确就会返回知乎首页
            # 拿到cookie才是目的！
            if end_url == "https://www.zhihu.com/":
                return self.get_cookies()
            else:
                # reload = self.browser.find_element_by_css_selector("#reload div")
                # self.browser.execute_script("arguments[0].click();", reload)
                time.sleep(3)

                k += 1

        return None

    def get_cookies(self):
        '''
        登录成功后 保存账号的cookies
        :return:
        '''
        cookies = self.browser.get_cookies()
        self.cookies = ''
        # cookie 要转换成字典的形式才可以用
        for cookie in cookies:
            self.cookies += '{}={};'.format(cookie.get('name'), cookie.get('value'))
        return cookies

    def __del__(self):
        self.browser.close()
        print('界面关闭')
        # self.display.stop()

class BaiduLogin():

    def __init__(self, ak, sk):
        """
        :param ak: API kEY
        :param sk: SECRET KEY
        """
        self.ak = ak
        self.sk = sk

    def get_access_token(self):
        # encoding:utf-8
        import requests

        # client_id 为官网获取的AK， client_secret 为官网获取的SK
        host = 'https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id=RO00QIMixnXaGmpxgzrrKv3H&client_secret=z7Rzjo3iPungqlvGXNS4jZoCNj0KTUsx'\
                .format(self.ak, self.sk)
        response = requests.get(host)
        if response.status_code == 200:
            return response.json()["access_token"]
        return None

    def recognize(self, access_token, image_file):
        """
        EasyDL 物体检测 调用模型公有云API Python3实现
        """

        import json
        import base64
        import requests
        """
        使用 requests 库发送请求
        使用 pip（或者 pip3）检查我的 python3 环境是否安装了该库，执行命令
          pip freeze | grep requests
        若返回值为空，则安装该库
          pip install requests
        """
        # download the pic and give it to API

        # 获取滑动前页面的url网址
        # 1. 获取原图


        # 目标图片的 本地文件路径，支持jpg/png/bmp格式
        IMAGE_FILEPATH = image_file

        # 可选的请求参数
        # threshold: 默认值为建议阈值，请在 我的模型-模型效果-完整评估结果-详细评估 查看建议阈值
        PARAMS = {"threshold": 0.3}

        # 服务详情 中的 接口地址
        MODEL_API_URL = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/detection/zh_slide"

        # 调用 API 需要 ACCESS_TOKEN。若已有 ACCESS_TOKEN 则于下方填入该字符串
        # 否则，留空 ACCESS_TOKEN，于下方填入 该模型部署的 API_KEY 以及 SECRET_KEY，会自动申请并显示新 ACCESS_TOKEN
        ACCESS_TOKEN = access_token
        API_KEY = "RO00QIMixnXaGmpxgzrrKv3H"
        SECRET_KEY = "z7Rzjo3iPungqlvGXNS4jZoCNj0KTUsx"

        print("1. 读取目标图片 '{}'".format(IMAGE_FILEPATH))
        with open(IMAGE_FILEPATH, 'rb') as f:
            base64_data = base64.b64encode(f.read())
            base64_str = base64_data.decode('UTF8')
        print("将 BASE64 编码后图片的字符串填入 PARAMS 的 'image' 字段")
        PARAMS["image"] = base64_str

        if not ACCESS_TOKEN:
            print("2. ACCESS_TOKEN 为空，调用鉴权接口获取TOKEN")
            auth_url = "https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials" \
                       "&client_id={}&client_secret={}".format(API_KEY, SECRET_KEY)
            auth_resp = requests.get(auth_url)
            auth_resp_json = auth_resp.json()
            ACCESS_TOKEN = auth_resp_json["access_token"]
            print("新 ACCESS_TOKEN: {}".format(ACCESS_TOKEN))
        else:
            print("2. 使用已有 ACCESS_TOKEN")

        print("3. 向模型接口 'MODEL_API_URL' 发送请求")
        request_url = "{}?access_token={}".format(MODEL_API_URL, ACCESS_TOKEN)
        response = requests.post(url=request_url, json=PARAMS)
        response_json = response.json()
        response_str = json.dumps(response_json, indent=4, ensure_ascii=False)
        # 坑：response_json不能代替response.json()来获取其中的字典值
        if "results" not in response_json:
            return None
        if len(response.json()["results"]) == 0:
            return None
        if "location" not in response.json()["results"][0]:
            return None
        # print("结果:\n{}".format(response_str))
        return response.json()["results"][0]["location"]["left"]


if __name__ == "__main__":
    # opencv识别验证码可能失败，机器学习识别概率高 6表示重试次数
    l = Login("18961275110", "86355573_aA", 6)
    l.login()

    # baidu = BaiduLogin("RO00QIMixnXaGmpxgzrrKv3H", "z7Rzjo3iPungqlvGXNS4jZoCNj0KTUsx")
    # print(baidu.recognize(baidu.get_access_token()))
