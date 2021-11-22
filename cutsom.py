import os,sys,json,requests
from selenium import webdriver
from bs4 import BeautifulSoup
from cdqa.utils.converters import pdf_converter
from cdqa.pipeline import QAPipeline
from cdqa.utils.download import download_model
from flask import Flask, request, jsonify
import pandas as pd, numpy as np, json , re , traceback
from ast import literal_eval 
from html.parser import HTMLParser
import urllib.request
from io import StringIO
from tika import parser
from flask_cors import CORS
from urllib.parse import unquote


app = Flask(__name__)
cors = CORS(app, resources={r"/foo": {"origins": "http://localhost:port"}})


@app.route('/',methods=['GET', 'POST'])
def hello():
    company = unquote(request.args.get('company', default = "none", type = str))
    pdf = unquote(request.args.get('pdfLink', default = "none", type = str))
    print(company , pdf)
    response = jsonify({'company': company , 'pdf':pdf})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

def get_article(company_name):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome('chromedriver',chrome_options=chrome_options)
    main = "https://www.google.com/search?q=site:https://www.reuters.com/%20gender+diversity+"+company_name
    driver.get(main)
    soup = BeautifulSoup(driver.page_source)
    output = {}
    try:
        info = soup.find('span' , {'class':'hgKElc'})
        print(info.get_text())
    except:
        try:
            ch = soup.find_all("div",{"class":"VwiC3b yXK7lf MUxGbd yDYNvb lyLwlc lEBKkf"})
            links = soup.find_all("div" , {"class":"yuRUbf"})
            main = ""
            for i in range(1):
                main += ch[i].get_text()
                content = ch[i].find_all('span')
                if(len(content)==1):
                    text = content[0].get_text()
                    date = 'Not available'
                    link = links[i].find('a')['href'] 
                else:
                    date = content[0].get_text()
                    text = content[1].get_text()
                    link = links[i].find('a')['href'] 
                output['date'] = date
                output['text'] = text
                output['link'] = link
            return output
        except:
            return "Couldn't collect articles for this arguments"   


def primer(obj):
    HEADERS = {
    "Authorization": "Bearer F-QLsteQEIMPHKXdlpRUHVlDZySVq6R4Jwyr1mkcrg8",
    "Content-Type": "application/json",
    }
    body = { "text": obj['link'] }
    response = requests.post("https://engines.primer.ai/api/v1/extract/scrape", headers=HEADERS, json=body)
    return response.json()['text']

def file_taker(data, min_length=200, include_line_breaks=False):    
    df = pd.DataFrame(columns=["title", "paragraphs"])
    df.loc[0] = ["title", None]
    s = data.strip()
    tparagraphs = re.split("\n\n(?=\u2028|[A-Z-0-9])", s)
    paragraphs = tparagraphs + tparagraphs
    list_par = []
    temp_para = ""  # variable that stores paragraphs with length<min_length
    # (considered as a line)
    for p in paragraphs:
        if not p.isspace():  # checking if paragraph is not only spaces
            if include_line_breaks:  # if True, check length of paragraph
                if len(p) >= min_length:
                    if temp_para:
                        # if True, append temp_para which holds concatenated
                        # lines to form a paragraph before current paragraph p
                        list_par.append(temp_para.strip())
                        temp_para = (
                            ""
                        )  # reset temp_para for new lines to be concatenated
                        list_par.append(
                            p.replace("\n", "")
                        )  # append current paragraph with length>min_length
                    else:
                        list_par.append(p.replace("\n", ""))
                else:
                        # paragraph p (line) is concatenated to temp_para
                    line = p.replace("\n", " ").strip()
                    temp_para = temp_para + f" {line}"
            else:
                # appending paragraph p as is to list_par
                list_par.append(p.replace("\n", ""))
        else:
            if temp_para:
                list_par.append(temp_para.strip())

        df.loc[0, "paragraphs"] = list_par
    return df

def fetcher(men,women,pages=[]):
    output = {}
    if men[1]>women[1]:
        output['Men_percentage'] = men[0]
        output['Women_percentage'] = None
        if(len(pages)==2):
            output['page'] = pages[0]
        else: 
            output['page'] = None
    else :
        output['Men_percentage'] = None
        output['Women_percentage'] = women[0]
        if(len(pages)==2):
            output['page'] = pages[1]
        else: 
            output['page'] = None
    return output

def CDQA(data):
    df = file_taker(data= data )
    pd.set_option('display.max_colwidth',-1)
    cqda_pipeline = QAPipeline(reader='./models/bert_qa.joblib',max_df = 1.0)
    cqda_pipeline.fit_retriever(df = df)
    query = "Percentage of women?"
    prediction = cqda_pipeline.predict(query,n_predictions= 1)
    women = [prediction[0][0],prediction[0][3]]
    query = "Percentage of men?"
    prediction = cqda_pipeline.predict(query,n_predictions= 1)
    men = [prediction[0][0],prediction[0][3]]
    return fetcher(men,women)

def CDQA_CO2(data):
    df = file_taker(data= data )
    pd.set_option('display.max_colwidth',-1)
    cqda_pipeline = QAPipeline(reader='./models/bert_qa.joblib',max_df = 1.0)
    cqda_pipeline.fit_retriever(df = df)
    query = "How much tonnes of co2 equivalent?"
    prediction = cqda_pipeline.predict(query,n_predictions= 1)
    return prediction[0][0]

def wrapper(company_name):
    try:
        obj = get_article(company_name)
    except Exception as e:
        return "Errors in Input" + e
    try: 
        text = primer(obj)
    except Exception as e:
        return "Error with Primer" + e
    try: 
        answer_json = CDQA(text)
        answer_json['date'] = obj['date']
        answer_json['link'] = obj['link']
        return answer_json
    except Exception as e:
        return "Error with Primer" + e

def download_file(download_url, filename):
    response = urllib.request.urlopen(download_url)    
    file = open(filename + ".pdf", 'wb')
    file.write(response.read())
    file.close()


def evaluate(file_url , queries = [],flag=None):
    output = []
    try:
        download_file(file_url, "Test")
        pd.set_option('display.max_colwidth',-1)
        df = pdf_converter(directory_path= "./" )
        pd.set_option('display.max_colwidth',-1)
        cqda_pipeline = QAPipeline(reader='./models/bert_qa.joblib',max_df = 1.0)
        cqda_pipeline.fit_retriever(df = df)
        for query in queries:
            local = {}
            print(query)
            prediction = cqda_pipeline.predict(query,n_predictions= 1)
            collect = []
            score = []
            answers = []
            for it in prediction:
                answers.append(it[0])
                collect.append(it[2])
                score.append(it[3])
            print(answers)
            pdf = "Test.pdf"
            file_data = []
            _buffer = StringIO()
            data = parser.from_file(pdf, xmlContent=True)
            xhtml_data = BeautifulSoup(data['content'],features="html.parser")
            for page, content in enumerate(xhtml_data.find_all('div', attrs={'class': 'page'})):
                _buffer.write(str(content))
                parsed_content = parser.from_buffer(_buffer.getvalue())
                _buffer.seek(0) 
                _buffer.truncate()
                file_data.append({'page': str(page+1), 'content': parsed_content['content']})
            for i in range(len(file_data)):
                pageno=i+1
                nn = file_data[i]['content'].strip()
                para = re.split("\n\n(?=\u2028|[A-Z-0-9])", nn)
                _par = []
                _para = ""  
                for p in para:
                    if not p.isspace():  # checking if paragraph is not only spaces
                        _par.append(p.replace("\n", ""))
                    else:
                        if _para:
                            _par.append(_para.strip())
                for substrings in collect:
                    if substrings in _par:
                        local['answer'] = answers[0]
                        local['pageno'] = pageno
                        local['score'] = score[0]
                        output.append(local)

        if flag == 'co2':
            return output
        if(len(output)==2):
            return fetcher([output[0]['answer'],output[0]['score']],[output[1]['answer'],output[1]['score']],[output[0]['pageno'],output[0]['pageno']])
        return "Analysis complete, cannot catch results"

    except Exception as e:
        return e



@app.route('/gender_diversity', methods=['GET', 'POST'])    
def gender_diversity():
    try:
        try:
            output = {} 
            company = unquote(request.args.get('company', default = "none", type = str))
            print(company)
            output['aricles_based'] = wrapper(company_name=company)
        except : 
            response = jsonify("parameter:company is not given")
        try: 
            pdf_link = unquote(request.args.get('pdfLink', default = "none", type = str))
            print(pdf_link)
            if(pdf_link!='none' and pdf_link!=""):
                try: 
                    output['pdf_based'] = evaluate(pdf_link,queries = ["Percentage of male employees?","Percentage of female employees?"])
                except:
                    response = jsonify(output)
                    # response.headers.add('Access-Control-Allow-Origin', '*')
                    # return response
        except : 
            response = jsonify(output)
            # response.headers.add('Access-Control-Allow-Origin', '*')
            # return response
        response = jsonify(output)
        # response.headers.add('Access-Control-Allow-Origin', '*')
        # return response
    except:
        response = jsonify("Input Errors")
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


def co2_resolver(arg,content):
    try:
        return content[arg].get_text()
    except:
        return "Not Available"

def get_co2_info(company_name):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome('chromedriver',chrome_options=chrome_options)
    output = {}
    main = "https://www.google.com/search?q=co2+equivalent+of+"+company_name
    driver.get(main)
    soup = BeautifulSoup(driver.page_source)
    try:
        info = soup.find('div' , {'class':'ifM9O'})
        content = info.find_all('span')
        output['text'] = co2_resolver(0,content)
        output['date'] = co2_resolver(2,content)
        try:
            output['link'] = info.find('a')['href']
        except:
            output['link'] = "Not Available"
        return output
    except:
        try:
            ch = soup.find_all("div",{"class":"VwiC3b yXK7lf MUxGbd yDYNvb lyLwlc lEBKkf"})
            links = soup.find_all("div" , {"class":"yuRUbf"})
            main = ""
            for i in range(1):
                content = ch[i].find_all('span')
                if len(content)==1:
                    text = co2_resolver(0,content)
                    date = 'Not available'
                    link = links[i].find('a')['href'] 
                else:
                    date = co2_resolver(0,content)
                    text = co2_resolver(1,content)
                    link = links[i].find('a')['href'] 
                output['date'] = date
                output['text'] = text
                output['link'] = link
            return output
        except:
            return json.dumps("Couldn't collect information for this arguments")

def co2_wrapper(company_name):
    try:
        obj = get_co2_info(company_name)
    except Exception as e:
        return "Errors in Input" + e
    try: 
        text = obj['text']
    except Exception as e:
        return "Error with web results" + e
    try: 
        obj['CO2_equivalent'] = CDQA_CO2(text)
        return obj
    except Exception as e:
        return "Error with Primer" + e


@app.route('/carbon_emission', methods=['GET', 'POST'])
def carbon_emission():
    try:
        try: 
            company = unquote(request.args.get('company', default = "none", type = str))
            print(company)
        except:
            response = jsonify("parameter:company is not given")
        try : 
            result = {}
            output_web_based = co2_wrapper(company_name=company)
            result['web_based'] = output_web_based
        except:
            response = jsonify("Couldn't process the request ")
        try: 
            pdf_link = unquote(request.args.get('pdfLink', default = "none", type = str))
            print(pdf_link)
            if(pdf_link!='none' and pdf_link!=""):
                try: 
                    output_pdf_based = evaluate(pdf_link,queries = ["Number of cabon emission by the company?"],flag='co2')
                    result['pdf_based'] = output_pdf_based
                except: 
                    response = jsonify(output_web_based)
        except : 
            response = jsonify(output_web_based)
        response = jsonify(result)
    except:
        response = jsonify("Input Errors")
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

if __name__ == '__main__':
    port = 8080 # If you don't provide any port the port will be set to ramdom ports
    cqda_pipeline = QAPipeline(reader='./models/bert_qa.joblib',max_df = 1.0)
    print ('Successfully Launched')
    app.run(host='0.0.0.0' , port=port, debug=True)