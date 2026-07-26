from email import header
from email.mime import base
import requests
import base64
from bs4 import BeautifulSoup
import pytesseract
from PIL import Image as pimg
from wand.image import Image as wimg
import numpy
import io
import re
from urllib.parse import urljoin
from db import Database
import os
import time
from requests.packages import urllib3
import logging
from datetime import date


class Extractor:
    def __init__(self, baseDomain, indexUrl, resultUrl, debug: bool = False):
        try:
            # Initializing important vars
            self.baseDomain = baseDomain
            # debug can be enabled via parameter or EXTRACTOR_DEBUG env var (1/true)
            env_debug = os.getenv('EXTRACTOR_DEBUG', '')
            env_flag = str(env_debug).lower() in ('1', 'true', 'yes')
            self.debug = bool(debug) or env_flag

            # Only windows needs this binary
            if os.name == 'nt':
                self.tesseractPath = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            self.session = requests.Session()
            self.session.trust_env = False
            self.headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
            # configure pytesseract command only if path exists on attribute
            try:
                pytesseract.pytesseract.tesseract_cmd = self.tesseractPath
            except Exception:
                # ignore if attribute not set on non-windows
                pass
            self.indexUrl = indexUrl
            self.resultUrl = resultUrl
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            self.db = Database(os.getcwd())

            # setup logger
            self._setup_logger()
            self.logger.debug(f"Extractor initialized (baseDomain={self.baseDomain}, indexUrl={self.indexUrl}, resultUrl={self.resultUrl}, debug={self.debug})")
        except Exception:
            # initialization problems should be visible in logs
            try:
                # ensure logger exists
                self._setup_logger()
                self.logger.exception("Error while initializing extractor!")
            except Exception:
                pass
            raise

    def _setup_logger(self):
        # Create a per-instance logger, avoid duplicate handlers
        name = f"extractor.{id(self)}"
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            fmt = logging.Formatter('[%(levelname)s] %(asctime)s %(name)s: %(message)s', datefmt='%H:%M:%S')
            handler.setFormatter(fmt)
            self.logger.addHandler(handler)
        # set level based on debug flag
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

    def decodeCaptcha(self):
        try:
            # Fetching captcha image
            captchaUrl = urljoin(self.baseDomain, self.img_src)
            self.logger.debug(f"Fetching captcha from: {captchaUrl}")
            captchaPage = self.session.get(captchaUrl, headers=self.headers, verify=False)
            pic = wimg(blob=captchaPage.content)
            # Modifying Image to prepare for OCR
            pic.modulate(120)
            pic.modulate(150)
            pic.modulate(130)
            img_buffer = numpy.asarray(
                bytearray(pic.make_blob(format='png')), dtype='uint8')
            bytesio = io.BytesIO(img_buffer)
            # Performing OCR on image
            pil_img = pimg.open(bytesio)
            captcha_code = re.sub(
                '[\W_]+', '', pytesseract.image_to_string(pil_img))
            self.captchaCode = captcha_code
            self.logger.debug(f"Captcha decoded: {self.captchaCode!r}")
        except:
            self.logger.exception("Error occured while decoding captcha!")
            raise Exception("Error occured while decoding captcha!")

    def parseIndexPage(self):
        try:
            # Fetching index page [where you enter USN]
            self.logger.debug(f"Fetching index page: {self.indexUrl}")
            indexPage = self.session.get(self.indexUrl, headers=self.headers, verify=False, timeout=20)
            self.logger.debug(f"Index page fetched: status={indexPage.status_code}, len={len(indexPage.content)}")
            soup = BeautifulSoup(indexPage.content, "html.parser")
            # Setting important values
            captcha_tag = soup.find(alt="CAPTCHA code")
            if captcha_tag is None:
                self.logger.error("CAPTCHA image tag not found on index page")
                raise Exception("CAPTCHA image tag not found")
            self.img_src = captcha_tag['src']
            token_input = soup.find('input', {'name': 'Token'})
            if token_input is None or token_input.get('value') is None:
                self.logger.error("Token input not found on index page")
                raise Exception("Token input not found")
            self.token = token_input['value']
            js_token_input = soup.find('input', {'name': 'js_token'})
            self.indexPage = indexPage.text
            self.logger.debug(
                f"Index page parsed: img_src={self.img_src}, token_len={len(str(self.token))}, js_token_input={bool(js_token_input)}")
        except Exception as e:
            self.logger.exception("Error occured while parsing index page!")
            raise Exception("Error while parsing Index page!")

    def _parse_result_page_new(self, soup, usn, reval):
        whitespaceRegEx = re.compile(r'\s+')
        student_block = None
        semester_blocks = []
        blocks = soup.find_all('div', class_='col-md-12 table-responsive')
        for block in blocks:
            text = block.get_text(' ', strip=True)
            if 'University Seat Number' in text and 'Student Name' in text:
                student_block = block
            elif 'Subject Code' in text:
                semester_blocks.append(block)

        if student_block is None or not semester_blocks:
            self.logger.debug('New result page layout not detected')
            return False

        details = {}
        student_rows = student_block.find_all('div', class_='divTableRow')
        for row in student_rows:
            cols = row.find_all('div', class_='divTableCell')
            if len(cols) >= 2:
                key = cols[0].get_text(' ', strip=True)
                value = cols[1].get_text(' ', strip=True)
                details[key] = value
        usn = details.get('University Seat Number', '').strip()
        name = details.get('Student Name', '').strip()
        self.logger.debug(f"Parsed student from new layout: usn={usn} name={name}")
        if not usn or not name:
            self.logger.error('Missing student usn or name after parsing new result page')
            return False

        for block in semester_blocks:
            semester_label = block.find('div', style=lambda v: v and 'text-align:center' in v)
            if semester_label:
                sem = whitespaceRegEx.sub(' ', semester_label.get_text(' ', strip=True)).replace('Semester : ', '').strip()
            else:
                sem = 'Unknown'
            self.logger.debug(f"Processing semester block: {sem}")

            table_rows = block.find_all('div', class_='divTableRow')
            for row in table_rows[1:]:
                cells = row.find_all('div', class_='divTableCell')
                cellData = [whitespaceRegEx.sub(' ', val.get_text(' ', strip=True)).strip() for val in cells]
                if not cellData:
                    continue
                self.db.insertRecord(reval, usn.lower(), name, sem, *cellData)
                self.logger.debug(f"Inserted record for {usn.lower()} sem={sem} data_len={len(cellData)}")

        return True

    def _parse_result_page_legacy(self, soup, usn, reval):
        whitespaceRegEx = re.compile(r'\s+')
        tables = soup.find_all('div', {"class": "col-md-12 table-responsive"})
        if not tables:
            self.logger.debug('Legacy result page layout not detected')
            return False

        try:
            studentDetails = tables[0].table.find_all('b')
            usn = studentDetails[1].next_sibling.strip()
            name = studentDetails[3].next_sibling.strip()
            self.logger.debug(f"Parsed student from legacy layout: usn={usn} name={name}")
        except Exception:
            self.logger.exception('Failed to parse student details from legacy layout')
            return False

        for i in range(1, len(tables)):
            semester = tables[i].find_all('b')[0]
            sem = whitespaceRegEx.sub(' ', semester.get_text()).replace('Semester : ', '').strip()
            self.logger.debug(f"Processing legacy semester: {sem}")
            if reval:
                marksTable = semester.parent.parent.find_next_sibling()
            else:
                marksTable = semester.parent.find_next_sibling()

            if marksTable is None:
                self.logger.warning(f"Marks table not found for semester {sem} in legacy layout")
                continue

            tableRow = marksTable.find_all('div', {'class': 'divTableRow'})
            for row in range(1, len(tableRow)):
                cells = tableRow[row].find_all('div', {'class': 'divTableCell'})
                cellData = [whitespaceRegEx.sub(' ', val.text.strip()).strip() for val in cells]
                self.db.insertRecord(reval, usn.lower(), name, sem, *cellData)
                self.logger.debug(f"Inserted legacy record for {usn.lower()} sem={sem} data_len={len(cellData)}")

        return True

    def parseResultPage(self, usn, reval):
        js_token = base64.b64encode(
        f"student_access_{date.today().year}".encode()).decode()
        self.logger.debug(f"Posting result request for usn={usn} reval={reval} js_token={js_token}")
        post_headers = self.headers.copy()
        post_headers['Referer'] = self.indexUrl
        resultPage = self.session.post(self.resultUrl, data={
                                       'Token': self.token, 'lns': usn, 'captchacode': self.captchaCode, 'js_token': js_token}, headers=post_headers, verify=False, timeout=20)
        self.logger.debug(f"Result page fetched: status={resultPage.status_code}, len={len(resultPage.text)}")
        if len(resultPage.text) < 300:
            self.logger.debug("Result page body (short response): %s", resultPage.text)
        soup = BeautifulSoup(resultPage.text, 'html.parser')
        try:
            self.logger.debug(f"Result page status: {resultPage.status_code} len_index={len(self.indexPage)} len_result={len(resultPage.text)}")
            if resultPage.ok and ("nomenclature" in resultPage.text.lower() or soup.find('div', class_='divTable')):
                parsed = self._parse_result_page_new(soup, usn, reval)
                if parsed:
                    return True
                self.logger.debug('Falling back to legacy result page parser')
                return self._parse_result_page_legacy(soup, usn, reval)
            else:
                error_scripts = soup.find_all('script')
                if error_scripts:
                    error_text = ' '.join(script.get_text(' ', strip=True) for script in error_scripts)
                    captchaRegEx = re.compile(r'captcha', re.IGNORECASE)
                    if bool(captchaRegEx.search(error_text)) or (len(self.indexPage) == len(resultPage.text)):
                        self.logger.info("Captcha likely incorrect or redirected; retrying after delay")
                        time.sleep(5)
                        return self.extract(usn, reval)
                return False
        except Exception:
            self.logger.exception("Error occured while parsing result!")
            return False

    def extract(self, usn, reval):
        try:
            self.logger.debug(f"Starting extract for usn={usn} reval={reval}")
            self.parseIndexPage()
            self.decodeCaptcha()
            result = self.parseResultPage(usn, reval)
            self.logger.debug(f"Extraction result for {usn}: {result}")
            return result
        except Exception as e:
            self.logger.exception("Error occured while extracting!")
            return False
