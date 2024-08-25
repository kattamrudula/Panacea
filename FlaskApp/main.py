__author__ = "spark expedition"
__copyright__ = "Copyright 2023, UnFold"
__license__ = "GPL"
__version__ = "1.0.1"
__maintainer__ = "spark expedition"
__email__ = "spark.expedition@gmail.com"
__status__ = "Development"

# Import Statement
import mimetypes
import ntpath
from pathlib import Path
import pathlib
import PyPDF2
import math
import datetime
import time
import os
import subprocess
import csv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
import openpyxl
from flask import jsonify
from flask import render_template, url_for, json, session
from flask_cors import CORS, cross_origin
from flask import Flask, request, send_file, send_from_directory
import shutil
import nbformat
import json
from nbformat import read
from nbconvert.preprocessors import ExecutePreprocessor
from nbconvert import PythonExporter

from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import h5py
import numpy as np
from time import strptime
import pandas as pd
import logging
import re
# from datetime import datetime
import dill
import base64
from PIL import Image
import psycopg2
import requests
from flask import redirect
import os
import sqlite3
# from bcrypt import hashpw, gensalt, checkpw
import papermill as pm
import uuid
import cv2
import numpy as np
#from socketio_setup import socketio
import google.generativeai as genai
import json
import requests
import speech_recognition as sr
import moviepy.editor as mp
from pydub import AudioSegment 
from pydub.silence import split_on_silence 
from datetime import datetime, timedelta
from collections import defaultdict 
from langchain_community.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from codecarbon import track_emissions
from dotenv import load_dotenv
from dotenv import load_dotenv, find_dotenv
# import asyncio
# from asyncio import WindowsSelectorEventLoopPolicy

# asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['model'] = ""
app.config['mname'] = ""
app.config['vname'] = ""

# Create a global logger object
logger = logging.getLogger(__name__)

# Configure the logger to use Stackdriver Logging
# You can also set the logging level and format if needed
logging.basicConfig(level=logging.INFO)
# # creating logger
app.secret_key = os.urandom(24)  # Set a secret key for session management
workspace_dir_path = "../PatientData/"
_ = load_dotenv(find_dotenv())
GOOGLE_API_KEY = os.environ['GOOGLE_API_KEY']
genai.configure(api_key=GOOGLE_API_KEY)

@app.route('/get_patient_file',methods = ['GET','POST'])
def get_patient_file():
    userName = request.args.get("userName")
    wspName = request.args.get("wspName")
    filePath = request.args.get("filePath")
    folder_path = workspace_dir_path
    file_obj = folder_path + filePath
    return send_file(file_obj)

@app.route("/get_patient_files_info")
def get_patient_files_info():
    data = []
    dbParams = json.loads(request.args.get("dbParams"))
    userName = dbParams['userName']
    folderName = dbParams['selectedPatient']
    dir_path = workspace_dir_path+"/"+folderName
    summary_path = "static/OutputCache/Summary/"+folderName+"/"
    columns = ["ID","FileName","Summary","FilePath","UserName"]
    i = 0
    files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f)) and f.startswith(".")==False]
    print("Files",files)
    for l in files:
        i = i+1
        l_path = Path(l) 
        summary_file_path = summary_path+l_path.stem+".txt"
        f = open(summary_file_path,'r')
        summary = json.loads(f.read())["text"]
        tcrow=[i,l_path.name,summary,folderName+"/"+l,userName]
        data.append(dict(zip(columns, tcrow)))
    print(data)
    return json.dumps(data, indent=4) 

# Configure a route to handle the request for displaying the models
@app.errorhandler(500)
def handle_internal_server_error(e):
    response = jsonify(error=str(e))
    response.status_code = 500
    return response

# Configure a route to handle the request for displaying the models


@app.errorhandler(500)
def handle_internal_server_error(e):
    response = jsonify(error=str(e))
    response.status_code = 500
    return response


@app.route("/favicon.ico")
def favicon():
    return send_file(os.path.join(app.static_folder, "CDN/images/entity.jpg"))


@app.route('/')
@cross_origin()
def landing():
    return render_template("PanaceaLanding.html")

@app.route('/PrivacyPolicy')
@cross_origin()
def PrivacyPolicy():
    return render_template("PrivacyPolicy.html")

@app.route('/ServiceTerms')
@cross_origin()
def ServiceTerms():
    return render_template("ServiceTerms.html")

@app.route('/Feedback')
@cross_origin()
def Feedback():
    return render_template("Feedback.html")

@app.route('/login')
@cross_origin()
def login():
    return render_template("Landing.html")

@app.route('/MasterHeader')
@cross_origin()
def MasterHeader():
    return render_template("MasterHeader.html")

@app.route('/<htmlfile>')
def renderhtml(htmlfile):
    user = request.args.get('user')
    return render_template(htmlfile, user=user)


@app.route('/Query')
def Query():
    return render_template('QueryWhisperer.html')

@app.route('/Timeline')
def Timeline():
    return render_template('Timeline.html')
 
@app.route('/Prescriptions')
def Prescriptions():
    return render_template('Prescriptions.html')
 

@app.route('/Insights')
def Insights():
    return render_template('Panacea.html')

@app.route('/Compliance')
def Compliance():
    return render_template('Compliance.html')


def get_files(path):
    all_files = []
    for root, directories, files in os.walk(path):
        # print("++++++++++++++++=======================+++++++++++++")
        # print(root)
        for file in files:
            if file.endswith(".ipynb") and not os.path.isdir(os.path.join(root, file)) and not (
                    file.endswith("-checkpoint.ipynb")):
                all_files.append(os.path.join(root, file))
    # print("+++++++_______++++++++")

    return all_files


@app.route('/get_meta_data')
def get_metadata_dict():
    path = request.args.get('folder_path')
    files = get_files(path)
    # print("printing number of files")

    return files


@app.route("/get_patient_folders")
@track_emissions(output_dir="static",project_name="Panacea") 
def get_patient_folders():
    data = []
    dbParams = json.loads(request.args.get("dbParams"))
    userName = dbParams['userName']
    dir_path = workspace_dir_path
    print(dir_path)
    columns = ["name"]
    for l in os.listdir(dir_path):
        tcrow=[l]
        data.append(dict(zip(columns, tcrow)))
    print(data)
    return json.dumps(data, indent=4) 

@app.route("/gemini_query_file")
@track_emissions(output_dir="static",project_name="Panacea")
def gemini_query_file():
    dbParams = json.loads(request.args.get("dbParams"))
    filePath = dbParams['selectedFile']
    userQuery = dbParams['userQuery']
    print("Entered file query for file "+filePath)
    fileAbs = Path(filePath)
    extracted_filename = f"static/OutputCache/Extracted/{fileAbs.parent}/{fileAbs.stem}.txt"
    f = open(extracted_filename,'r',encoding= "utf-8")
    report = f.read()
    model = genai.GenerativeModel(model_name='gemini-1.5-pro-latest')
    prompt = f"""Provide answer to below question based on report provided.
    Question : {userQuery}
    Report: {report}""" 
    response = model.generate_content(prompt)
    try:
        returnData = response.candidates[0].content.parts[0].text
        return returnData
    except:
        returnData = response.text
        return returnData
    
"""Gemini"""
def gemini_summary(entity_report, reportName):
    entity = reportName.split('/')
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = "summarize the below report in 6 points numbered list maximum \n\n" + entity_report
    response = model.generate_content(prompt)
    cache_file_path = f"static/OutputCache/Gemini-SummaryContent-{entity[0]}.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    print("gemini_summary done")
    try:
        returnData = response.candidates[0].content.parts[0].text
        if len(returnData) > 10:
            f = open(cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.candidates[0].content.parts[0].text

    except:
        returnData = response.text
        if len(returnData) > 10:
            f = open(
                cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.text
    finally:
        # open and read the file after the overwriting:
        f = open(
            cache_file_path, "r", encoding='cp1252')
        return f.read()


def gemini_sentiment(entity_report, reportName):
    entity = reportName.split('/')
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = "provide the sentiment of  below report in any of the below options: Positive,Negative,Neutral. Return answer in form of json with key as Sentiment and value from given options.\n\n" + entity_report
    response = model.generate_content(prompt)
    cache_file_path = f"static/OutputCache/Gemini-SentimentContent-{entity[0]}.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    print("gemini_sentiment done")
    try:
        returnData = response.candidates[0].content.parts[0].text
        if len(returnData) > 6:
            f = open(cache_file_path
                , "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.candidates[0].content.parts[0].text

    except:
        returnData = response.text
        if len(returnData) > 6:
            f = open(
                cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.text
    finally:
        # open and read the file after the overwriting:
        f = open(
            cache_file_path, "r", encoding='cp1252')
        return f.read()


def gemini_NER(entity_report, reportName, domainName):
    entity = reportName.split('/')
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    # prompt = "provide the Named Entities such as hospital names, patient names, doctor names,locations,medication names, and dates mentioned in the patient report as json key value pairs \n\n" + entity_report
    # prompt = "provide the named entities such as who are the people involved, locations involved, datestamps, items or servers involved as json key value pairs \n\n"+ entity_report
    prompt = ""
    if domainName == "Clinical":
        prompt = "provide the Named Entities such as hospital names, patient names, doctor names,locations,medication names, and dates mentioned in the patient report as json key value pairs \n\n" + entity_report
    elif domainName == "Incidents":
        prompt = "provide the named entities such as who are the people involved, locations involved, dates involved, items or servers involved as json key value pairs \n\n" + entity_report
    elif domainName == "Manufacturing":
        prompt = "provide the named entities such as who are the people involved, locations involved, dates involved, items or products involved, costs involved as json key value pairs \n\n" + entity_report
    elif domainName == "Gas Supply":
        prompt = "provide the named entities such as who are the people involved, locations involved, dates involved, items involved, costs involved as json key value pairs \n\n" + entity_report
    elif domainName == "Cyber Security":
        prompt = "provide the named entities such as who are the people involved, locations involved, dates involved, risks and penalties involved, costs involved as json key value pairs \n\n" + entity_report
    else:
        prompt = "provide the named entities such as hospital names, patient names, doctor names,locations,medication names, and dates mentioned in the patient report as json key value pairs  \n\n" + entity_report
    response = model.generate_content(prompt)
    cache_file_path = f"static/OutputCache/Gemini-NERContent-{entity[0]}.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    print("gemini_NER done")
    # print(json.dumps(response))

    # Three PArameters - Response, OpenAI, NERContent.txt - FileName - OpenAI-NERContent.txt
    # Three PArameters - Response, Gemini, Sentiment.txt - FileName - Gemini-Sentiment.txt

    try:
        returnData = response.candidates[0].content.parts[0].text
        if len(returnData) > 10:
            f = open(cache_file_path
                , "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.candidates[0].content.parts[0].text

    except:
        returnData = response.text
        if len(returnData) > 10:
            f = open(
                cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.text
    finally:
        # open and read the file after the overwriting:
        f = open(
            cache_file_path, "r", encoding='cp1252')
        return f.read()


def gemini_emotion(entity_report, reportName):
    entity = reportName.split('/')
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = "Predict the emotion based on report from provided options : [ 'Happiness', 'Sadness', 'Anger', 'Fear', 'Suprise', 'Disgust']. Return answer in form of json with key as Emotion and value from given options.\n\n" + entity_report
    response = model.generate_content(prompt)
    print("gemini_emotion done")
    cache_file_path = f"static/OutputCache/Gemini-EmotionContent-{entity[0]}.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        returnData = response.candidates[0].content.parts[0].text
        if len(returnData) > 1:
            f = open(cache_file_path
                , "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.candidates[0].content.parts[0].text

    except:
        returnData = response.text
        if len(returnData) > 1:
            f = open(cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.text
    finally:
        # open and read the file after the overwriting:
        f = open(cache_file_path, "r", encoding='cp1252')
        return f.read()


def gemini_tone(entity_report, reportName):
    entity = reportName.split('/')
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = "Predict the Tone based on report from provided options : [ 'FORMAL', 'INFORMAL', 'OPTIMISTIC', 'HARSH']. Return answer in form of json with key as Tone and value from given options.\n\n" + entity_report
    response = model.generate_content(prompt)
    print("gemini_tone done")
    cache_file_path =f"static/OutputCache/Gemini-ToneContent-{entity[0]}.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        returnData = response.candidates[0].content.parts[0].text
        if len(returnData) > 1:
            f = open(cache_file_path
                , "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.candidates[0].content.parts[0].text

    except:
        returnData = response.text
        if len(returnData) > 1:
            f = open(cache_file_path, encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.text
    finally:
        # open and read the file after the overwriting:
        f = open(cache_file_path, "r", encoding='cp1252')
        return f.read()


def gemini_englishmaturity(entity_report, reportName):
    entity = reportName.split('/')
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = "Predict the English Maturity of the report from provided options : [ 'AVERAGE', 'MEDIUM', 'PROFICIENT', 'LOW']. Return answer in form of json with key as EnglishMaturity and value from given options.\n\n" + entity_report
    response = model.generate_content(prompt)
    print("gemini_englishmaturity done")
    cache_file_path = f"static/OutputCache/Gemini-EngmatContent-{entity[0]}.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        returnData = response.candidates[0].content.parts[0].text
        if len(returnData) > 1:
            f = open(cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.candidates[0].content.parts[0].text

    except:
        returnData = response.text
        if len(returnData) > 1:
            f = open(cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.text
    finally:
        # open and read the file after the overwriting:
        f = open(cache_file_path, "r", encoding='cp1252')
        return f.read()


def gemini_determine_sentiment_highlights(entity_report, reportName):
    entity = reportName.split('/')
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = "Given a Report \n\n" + entity_report + \
        "\n\n Provide the key words or phrases that strongly contribute to determining the sentiment of the report. Return answer in form of json with key as SentimentWords and value as list of identified words or phrases."
    response = model.generate_content(prompt)
    print("gemini_sentiment_highlights done")
    cache_file_path = f"static/OutputCache/Gemini-SentHighContent-{entity[0]}.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        returnData = response.candidates[0].content.parts[0].text
        if len(returnData) > 10:
            f = open(cache_file_path
                , "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.candidates[0].content.parts[0].text

    except:
        returnData = response.text
        if len(returnData) > 10:
            f = open(
                cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.text
    finally:
        # open and read the file after the overwriting:
        f = open(
            cache_file_path, "r", encoding='cp1252')
        return f.read()


def gemini_determine_tone_highlights(entity_report, reportName):
    entity = reportName.split('/')
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = "Given a Report \n\n" + entity_report + \
        "\n\n Provide the key words or phrases that strongly contribute to determining the tone of the report. Return answer in form of json with key as ToneWords and value as list of identified words or phrases"
    response = model.generate_content(prompt)
    print("gemini_tone_highlights done")
    cache_file_path = f"static/OutputCache/Gemini-ToneHighContent-{entity[0]}.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        returnData = response.candidates[0].content.parts[0].text
        if len(returnData) > 10:
            f = open(cache_file_path
                , "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.candidates[0].content.parts[0].text

    except:
        returnData = response.text
        if len(returnData) > 10:
            f = open(cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.text
    finally:
        # open and read the file after the overwriting:
        f = open(cache_file_path, "r", encoding='cp1252')
        return f.read()


def gemini_determine_emotion_highlights(entity_report, reportName):
    entity = reportName.split('/')
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = "Given a Report \n\n" + entity_report + \
        "\n\n Provide the key words or phrases that strongly contribute to determining the emotion of the report. Return answer in form of json with key as EmotionWords and value as list of identified words or phrases"
    response = model.generate_content(prompt)
    print("gemini_emotion_highlights done")
    cache_file_path = f"static/OutputCache/Gemini-EmoHighContent-{entity[0]}.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        returnData = response.candidates[0].content.parts[0].text
        if len(returnData) > 10:
            f = open(cache_file_path
                , "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.candidates[0].content.parts[0].text

    except:
        returnData = response.text
        if len(returnData) > 10:
            f = open(
                cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.text
    finally:
        # open and read the file after the overwriting:
        f = open(cache_file_path, "r", encoding='cp1252')
        return f.read()


def gemini_determine_englishmaturity_highlights(entity_report, reportName):
    entity = reportName.split('/')
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = "Given a Report \n\n" + entity_report + \
        "\n\n Provide the key words or phrases that strongly contribute to determining the English Maturity of the report. Return answer in form of json with key as EngMatWords and value as list of identified words or phrases"
    response = model.generate_content(prompt)
    print("gemini_englishmaturity_highlights done")
    cache_file_path = f"static/OutputCache/Gemini-EngmatHighContent-{entity[0]}.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        returnData = response.candidates[0].content.parts[0].text
        if len(returnData) > 10:
            f = open(cache_file_path
                , "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.candidates[0].content.parts[0].text

    except:
        returnData = response.text
        if len(returnData) > 10:
            f = open(cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.text
    finally:
        # open and read the file after the overwriting:
        f = open(cache_file_path, "r", encoding='cp1252')
        return f.read()

@app.route("/get_valid_rag_queries")
@track_emissions(output_dir="static",project_name="Panacea")
def get_valid_rag_queries():
    queries = ["What are the medicines prescribed?","When is the patient registered?"]
    return queries

def create_rag_model():
    prompt_template = """
    Answer the question as detailed as possible from the provided context, make sure to provide all the details\n\n
    Context:\n {context}?\n
    Question: \n{question}\n

    Answer:
    """

    model = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest",
                                   temperature=0.3)

    prompt = PromptTemplate(template=prompt_template,
                            input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain


def create_vector_db(patient_report):
    # code to extract text from folder files
    text = patient_report
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=256, chunk_overlap=20)
    text_chunks = text_splitter.split_text(text)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")
    
@app.route("/create_search_query")
@track_emissions(output_dir="static",project_name="Panacea")
def create_search_query():
    dbParams = json.loads(request.args.get("dbParams"))
    reportName = "RAG"
    user_question = dbParams['userQuestion']
    entity = reportName.split('_')
    print(dbParams)
    # entity_report = ""
    # for file in filesList:
    #     entity_report += pdf_2_txt("../Workspace/"+userName +
    #                                "/"+workspaceName+"/DataFiles/"+file) + "\n\n"
    # create_vector_db(entity_report)
    # print("db created")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    new_db = FAISS.load_local("static/faiss_index_medical", embeddings)
    print("db loaded")
    docs = new_db.similarity_search(user_question)
    print("docs searched")
    chain = create_rag_model()
    print("rag model created")

    try:
        response = chain(
            {"input_documents": docs, "question": user_question}, return_only_outputs=True)
        if response:
            f = open(
                f"static/OutputCache/RAG/Gemini-RAG-{entity[0]}.txt", "w", encoding='utf-8')
            f.write(json.dumps(response))
            f.close()
        return response
    except:
        f = open(
            f"static/OutputCache/RAG/Gemini-RAG-{entity[0]}.txt", "r", encoding='utf-8')
        return f.read()
    
@app.route("/validate_search_query")
@track_emissions(output_dir="static",project_name="Panacea")
def validate_search_query():   
    dbParams = json.loads(request.args.get("dbParams"))
    user_question = dbParams['userQuestion']
    query_validations = [
        {
            "query":"get me the contract summary of customer WakeFit",
            "status":"BLOCKED",
            "detection":"DOCUMENT LEVEL SECURITY",
            "description":"You don't have access to the document to fetch this information",
            "alternate": "Try same query with customers you have access to."
        },
        {
            "query":"get me the sales data for country Srilanka",
            "status":"BLOCKED",
            "detection":"ROW LEVEL SECURITY",
            "description":"You dont have access to the data of this country.",
            "alternate": "Try accessing India, Nepal, Burma - available for your role"
        },
        {
            "query":"get me the commission percentage for segment Premium Cars",
            "status":"BLOCKED",
            "detection":"COLUMN LEVEL SECURITY",
            "description":"You dont have access to commission percentage of this segment.",
            "alternate":"Get me the target sales for segment"
        },
        {
            "query":"get me the sales values of customer with pancard BAJPC4350M",
            "status":"BLOCKED (risk score:0.8)<icon>",
            "detection":"PII DETECTED",
            "description":"PII information is detected",
            "alternate":"Get me the target sales for customer name [ ]"
        },
        {
            "query":"get me the sales values of customer Rakesh Gupta and mobile 8734646664",
            "status":"MASKED",
            "detection":"PII DETECTED",
            "description":"As PII information is detected, masked this information in prompt",
            "alternate":"get me the sales values of customer Rakesh Gupta and mobile 8XXXXXXXX4"
        },
        {
            "query":"get me the sales number for current quarter Q4-2024",
            "status":"BLOCKED",
            "detection":"PERSONA PERMISSIONS",
            "description":"You dont have permission to read the data of current quarter.",
            "alternate":"Try for previous quarters."
        },
        {
            "query":"show me the sales forecast for France",
            "status":"BLOCKED",
            "detection":"MODEL LEVEL SECURITY",
            "description":"You dont have access to the Sales Forecast model.",
            "alternate":"Try accessing other models"
        },
        {
            "query":"Show me the sales for retail segment Q4-2024",
            "status":"BLOCKED",
            "detection":"INSIDER TRADING VIOLATION",
            "description":"You dont have permission to read the data of current quarter as this may lead to insider trading",
            "alternate":"Try for previous quarters"
        },
        {
            "query":"Show me the technical details of submarine",
            "status":"BLOCKED",
            "detection":"COPYRIGHT VIOLATION",
            "description":"This information cannot be accessed as it is a violation of copyright",
            "alternate":"Try any other details"
        },
        {
            "query":"Show me the technical details of submarine",
            "status":"BLOCKED",
            "detection":"RECRUITMENT/PERSONAL",
            "description":"This information cannot be accessed as it is a violation of copyright",
            "alternate":"Try any other details"
        },
        {
            "query":"Show me the technical details of submarine",
            "status":"BLOCKED",
            "detection":"SELF HARMING",
            "description":"This information cannot be accessed as it is a violation of copyright",
            "alternate":"Try any other details"
        },
        {
            "query":"Show me the technical details of submarine",
            "status":"BLOCKED",
            "detection":"DATA MANIPULATION/POISONING",
            "description":"This information cannot be accessed as it is a violation of copyright",
            "alternate":"Try any other details"
        },
        {
            "query":"Show me the technical details of submarine",
            "status":"BLOCKED",
            "detection":"VIOLENT ACTION",
            "description":"This information cannot be accessed as it is a violation of copyright",
            "alternate":"Try any other details"
        },
        {
            "query":"Show me the technical details of submarine",
            "status":"BLOCKED",
            "detection":"DATA DELETION",
            "description":"This information cannot be accessed as it is a violation of copyright",
            "alternate":"Try any other details"
        },
        {
            "query":"Show me the technical details of submarine",
            "status":"BLOCKED",
            "detection":"JAIL BREAKING",
            "description":"This information cannot be accessed as it is a violation of copyright",
            "alternate":"Try any other details"
        }
    ]
    check_exists = [q for q in query_validations if q["query"]==user_question]
    if len(check_exists) == 0:
        return {
            "message" :"PASS"
        }
    else:
        return {
            "message":"BLOCKED",
            "data":check_exists[0],
        }
 
@app.route("/get_timeline")
@track_emissions(output_dir="static",project_name="Panacea")
def get_timeline():
    print("Etered timeline")
    dbParams = json.loads(request.args.get("dbParams"))
    workspace_path = workspace_dir_path
    folder = dbParams['selectedPatient']
    folder_path = workspace_path+"/"+folder
    filesList = [folder+"/"+str(filepath) for filepath in os.listdir(folder_path)]
    timeline = []
    for file in filesList:
        fileAbs = Path(file);
        file = Path(workspace_path+"/"+file)
        filename = f"static/OutputCache/Summary/{fileAbs.parent}/{fileAbs.stem}.txt"
        f = open(filename, "r", encoding='cp1252')
        summary_obj = json.loads(f.read())
        summary = summary_obj["text"]
        create_timestamp = file.stat().st_ctime
        create_time = datetime.fromtimestamp(create_timestamp)
        timeline.append({"Event Type":fileAbs.stem,"Event Description":summary,"Time":create_time})
    return timeline

@app.route("/gemini_results")
@track_emissions(output_dir="static",project_name="Panacea")
def gemini_results():

    dbParams = json.loads(request.args.get("dbParams"))
    domainName = dbParams['domainName']
    userName = dbParams['userName']
    workspace_path = workspace_dir_path
    folder = dbParams['selectedPatient']
    folder_path = workspace_path+"/"+folder
    filesList = [folder+"/"+str(filepath) for filepath in os.listdir(folder_path)]
    print(filesList)
    reportName = filesList[0]
    print(dbParams)
    print(reportName)
    input_tokens = 0
    output_tokens = 0
    entity_report = ""
    timeline = []
    for file in filesList:
        fileAbs = Path(file);
        file = Path(workspace_path+"/"+file)
        filename = f"static/OutputCache/Summary/{fileAbs.parent}/{fileAbs.stem}.txt"
        print(filename)
        f = open(filename, "r", encoding='cp1252')
        summary_obj = json.loads(f.read())
        summary = summary_obj["text"]
        input_tokens += summary_obj["input_tokens"]
        output_tokens += summary_obj["output_tokens"]
        create_timestamp = file.stat().st_ctime
        create_time = datetime.fromtimestamp(create_timestamp)
        timeline.append({"Event Type":fileAbs.stem,"Event Description":summary,"Time":create_time})
        entity_report += summary + "\n\n"
    output_json = {
        "completeReport": entity_report,
        "Summary": gemini_summary(entity_report, reportName),
        "Sentiment": gemini_sentiment(entity_report, reportName),
        "NER": gemini_NER(entity_report, reportName, domainName),
        "Emotion": gemini_emotion(entity_report, reportName),
        "Tone": gemini_tone(entity_report, reportName),
        "EnglishMaturity": gemini_englishmaturity(entity_report, reportName),
        "SentimentWords": gemini_determine_sentiment_highlights(entity_report, reportName),
        "EmotionWords": gemini_determine_emotion_highlights(entity_report, reportName),
        "ToneWords": gemini_determine_tone_highlights(entity_report, reportName),
        "EngMatWords": gemini_determine_englishmaturity_highlights(entity_report, reportName),
        "Timeline": timeline,
        "InputTokens": input_tokens,
        "OutputTokens": output_tokens
    }
    return output_json

@app.route('/get_folder_names')
@track_emissions(output_dir="static",project_name="Panacea")
def get_folder_names():
    data = []
    dbParams = json.loads(request.args.get("dbParams"))
    folderName = dbParams['folderName']
    userName = dbParams['userName']
    wspName = dbParams['wspName']
    dir_path = workspace_dir_path + '/' + folderName
    config_file_path = workspace_dir_path + '/' + 'Config.json'
    
    # Load the config JSON file
    with open(config_file_path, 'r') as config_file:
        config_data = json.load(config_file)

    # Initialize result list
    result = []

    # Function to get type based on folder name from config
    def get_folder_type(folder_name):
        for entry in config_data.get('Directory', []):
            if entry.get('Name') == folder_name:
                return entry.get('Type', 'Folder')
        return 'Folder'

    for root, dirs, files in os.walk(dir_path):
        if root == dir_path:  # Top-level dir_path
            result.extend([{"name": file, "type": "File"} for file in files])
        else:  # Subdirectories
            if os.path.relpath(root, dir_path) != "temp":
                folder_dict = {
                    "name": os.path.relpath(root, dir_path),
                    "type": get_folder_type(os.path.relpath(root, dir_path)),
                    "children": [{"name": file, "type": "File"} for file in files]
                }
                result.append(folder_dict)
    # print(result)

    return json.dumps(result)

@app.route("/gemini_aifeature_results")
@track_emissions(output_dir="static",project_name="Panacea")
def gemini_aifeature_results():
    dbParams = json.loads(request.args.get("dbParams"))
    filePath = dbParams['selectedFile']
    aiFeature = dbParams['aiFeature']
    userName = dbParams['userName']
    wspName = dbParams['wspName']
    workspace_path = workspace_dir_path
    reportName = filePath
    value = ""
    print(dbParams)
    print(reportName)
    output_json = {}
    if aiFeature == "Summary":
        fileAbs = Path(filePath);
        filename = f"static/OutputCache/Summary/{fileAbs.parent}/{fileAbs.stem}.txt"
        f = open(filename, "r", encoding='cp1252')
        value = f.read()
        output_json = {
            "Summary" : value
        }
    else:
        emotion = gemini_multimodal_aifeature(filePath, "Emotion",workspace_path)
        sentiment = gemini_multimodal_aifeature(filePath, "Sentiment",workspace_path)
        tone = gemini_multimodal_aifeature(filePath, "Tone",workspace_path)
        #english = gemini_multimodal_aifeature(filePath, "EnglishMaturity")
        output_json = {
            "Emotion" : emotion,
            "Sentiment" : sentiment,
            "Tone" : tone
            #"EnglishMaturity":english
        }
    
    return output_json

"""Utility function for text extraction"""
def pdf_2_txt(pdf_path):
    try:
        pdf_file = open(pdf_path, 'rb')
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text_content = ' '
        for page_number in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_number]
            text_content += page.extract_text()
        pdf_file.close()
        text_content = re.sub(r'\s+', ' ', text_content)
    except Exception as e:
        print("Error:", e)
    return text_content

@app.route("/find_medical_department")
@track_emissions(output_dir="static",project_name="Panacea")
def find_medical_department():
    dbParams = json.loads(request.args.get("dbParams"))
    folder = dbParams['selectedPatient']
    userName = dbParams['userName']
    wspName = dbParams['wspName']
    workspace_path = workspace_dir_path
    folder_path = workspace_path+"/"+folder
    filesList = [folder+"/"+str(filepath) for filepath in os.listdir(folder_path) if Path(filepath).suffix != ""]
    entity_report = ""
    for file in filesList:
        print(file)
        # if ".pdf" in file["name"] :
        #     entity_report += pdf_2_txt(workspace_dir_path+"/DataFiles/"+file["absPath"]) + "\n\n"
        # else:
        summary = gemini_multimodal_summary(file,workspace_path)
        entity_report += summary
    entity = filesList[0].split('/')[0]
    # model = genai.GenerativeModel('gemini-1.5-pro-latest')
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = """Identify  the medical department of the below report from the given options :
                
                ['Anesthesiology','Cardiology','Dermatology','Emergency Medicine','Endocrinology','Gastroenterology','General Surgery','Geriatrics','Hematology',
                'Infectious Diseases','Internal Medicine','Nephrology','Neurology','Neurosurgery','Obstetrics and Gynecology (OB/GYN)','Oncology','Ophthalmology',
                'Orthopedics','Otolaryngology (ENT)','Pathology','Pediatrics','Physical Medicine and Rehabilitation','Plastic Surgery','Podiatry','Psychiatry','Pulmonology',
                'Radiology','Rheumatology','Thoracic Surgery','Urology','Vascular Surgery']. 
                
                If no department is identified from above options, then return response as 'General Medicine'.
                
                Return response in form of json with key as Department and value as identified medical department.
                \n\n""" + entity_report 
    print("gemini finding medical department")
    cache_file_path = f"static/OutputCache/gemini-MEDICAL-DEPARTMENT-{entity}.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        response = model.generate_content(prompt)
        returnData = response.candidates[0].content.parts[0].text
        f = open(cache_file_path, "w", encoding='cp1252')
        f.write(returnData)
        f.close()
        return returnData
    except:
        response = model.generate_content(prompt)
        returnData = response.text
        f = open(cache_file_path, "w", encoding='cp1252')
        f.write(returnData)
        f.close()
        return returnData
    finally:
        # open and read the file after the overwriting:
        f = open(cache_file_path, "r", encoding='cp1252')
        print("gemini finding medical department done in finally")
        return f.read()

def extract_video_text(filePath):
    video_text = ""
    video_file_path = filePath
    clip = mp.VideoFileClip(video_file_path)
    clip.audio.write_audiofile(r"static/temp/videoconverted.wav")
    audio = AudioSegment.from_wav(r"static/temp/videoconverted.wav")
    n = len(audio)
    counter = 1
    interval = 20 * 1000
    overlap = 1.5 * 1000
    start = 0
    end = 0
    flag = 0
    # chunks = split_on_silence(audio,min_silence_len = 500, silence_thresh = -40) 
    Path(r'static/temp/video_chunks').parent.mkdir(parents=True,exist_ok=True) 
    # print(chunks)
    for i in range(0, 2 * n, interval):
        if i == 0:
            start = 0
            end = interval
        else:
            start = end - overlap
            end = start + interval 
    
        if end >= n:
            end = n
            flag = 1
    
        audio_chunk = audio[start:end]
    
        # Filename / Path to store the sliced audio
        filename = 'chunk'+str(counter)+'.wav'
        file = "static/temp/video_chunks/"+filename 
        audio_chunk.export(file,format="wav")
        print("Processing chunk "+str(counter)+". Start = "
                        +str(start)+" end = "+str(end))
        counter = counter + 1
        r = sr.Recognizer() 
        try:
            with sr.AudioFile(file) as source: 
                audio_listened = r.listen(source) 
                rec = r.recognize_google(audio_listened) 
                video_text += rec + " "
        except:
            pass
    return video_text

def extract_audio_text(filePath):
    audio_text = ""
    audio_file_path = filePath
    clip = mp.AudioFileClip(audio_file_path)
    clip.write_audiofile(r"static/temp/audioconverted.wav")
    audio = AudioSegment.from_wav(r"static/temp/audioconverted.wav")
    n = len(audio)
    counter = 1
    interval = 20 * 1000
    overlap = 1.5 * 1000
    start = 0
    end = 0
    flag = 0
    # chunks = split_on_silence(audio,min_silence_len = 500, silence_thresh = -40) 
    Path(r'static/temp/audio_chunks').parent.mkdir(parents=True,exist_ok=True) 
    # print(chunks)
    for i in range(0, 2 * n, interval):
        if i == 0:
            start = 0
            end = interval
        else:
            start = end - overlap
            end = start + interval 
    
        if end >= n:
            end = n
            flag = 1
    
        audio_chunk = audio[start:end]
    
        # Filename / Path to store the sliced audio
        filename = 'chunk'+str(counter)+'.wav'
        file = "static/temp/audio_chunks/"+filename 
        audio_chunk.export(file,format="wav")
        print("Processing chunk "+str(counter)+". Start = "
                        +str(start)+" end = "+str(end))
        counter = counter + 1
        r = sr.Recognizer() 
        try:
            with sr.AudioFile(file) as source: 
                audio_listened = r.listen(source) 
                rec = r.recognize_google(audio_listened) 
                audio_text += rec + " "
        except:
            pass
    return audio_text

# @app.route("/gemini_multimodal_summary")
def gemini_multimodal_summary(filePath,workspace_path):
    # dbParams = json.loads(request.args.get("dbParams"))
    # filePath = dbParams['selectedFile']
    input_tokens = 0
    output_tokens = 0
    print("Entered multimodal summary for file "+filePath)
    fileAbs = Path(filePath)
    file = Path(workspace_path+"/"+filePath)
    file_path = workspace_path+"/"+filePath
    print(filePath)
    filename = f"static/OutputCache/Summary/{fileAbs.parent}/{fileAbs.stem}.txt"
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    extracted_filename = f"static/OutputCache/Extracted/{fileAbs.parent}/{fileAbs.stem}.txt"
    extracted_path = Path(extracted_filename)
    extracted_path.parent.mkdir(parents=True, exist_ok=True)
    #entity = str(filePath).split('/')[0]
    try:
        generation_config = {
            "temperature":0.9,
            "top_p":1,
            "top_k":0,
            "max_output_tokens":4096
        }
        safety_settings = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        ]
        model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest",
                                            generation_config=generation_config,
                                            safety_settings=safety_settings)
        if str(filePath).split('.')[-1]=="pdf":
            # patient_report = pdf_2_txt(file)
            patient_report = get_ocr_content(file_path)
            with open(extracted_filename,"w",encoding = "utf-8") as f:
                f.write(patient_report)
                print("written extracted text to file")
            prompt = "provide the summary of the below patient report"+patient_report
            response = model.generate_content(prompt)
            input_tokens = response.usage_metadata.prompt_token_count 
            output_tokens = response.usage_metadata.candidates_token_count
            out_obj = {"input_tokens":input_tokens,"output_tokens":output_tokens,"text":""}
            try:
                returnData = response.candidates[0].content.parts[0].text
                if returnData:
                    out_obj["text"] = returnData
                    with open(filename,"w") as f:
                        f.write(json.dumps(out_obj))
                        print("written to text file")
                return returnData
            except:
                returnData = response.text
                if returnData:
                    out_obj["text"] = returnData
                    with open(filename,"w") as f:
                        f.write(json.dumps(out_obj))
                        print("written to text file")
                return returnData
            finally:
                f=open(filename,'r')
                return f.read()
        elif str(filePath).split('.')[-1]=="png" or filePath.split('.')[-1]=="jpeg" or filePath.split('.')[-1]=="jpg":
            try:
                image_parts = [
                    {
                        "mime_type": "image/jpeg", ## Mime type are PNG - image/png. JPEG - image/jpeg. WEBP - image/webp
                        "data": file.read_bytes()
                    }
                ]
                system_prompt = """
                        You are a radiologist expert in interpreting MRI scanning reports and identifies abnormalities to provide accurate diagnoses..
                        Input images in the form of MRI sacnning images  will be provided to you,
                        and your task is to respond to questions based on the image.
                        """
                
                user_prompt = "What specific abnormalities or findings were identified in the MRI brain scan image?"
                input_prompt= [system_prompt, image_parts[0], user_prompt]
                response = model.generate_content(input_prompt)
                input_tokens = response.usage_metadata.prompt_token_count 
                output_tokens = response.usage_metadata.candidates_token_count
                out_obj = {"input_tokens":input_tokens,"output_tokens":output_tokens,"text":""}
                returnData = response.Candidates[0].content.parts[0].text
                if returnData:
                    out_obj["text"] = returnData
                    with open(filename,"w") as f:
                        f.write(json.dumps(out_obj))
                return returnData
            except:
                returnData = response.text
                if returnData:
                    out_obj["text"] = returnData
                    with open(filename,"w") as f:
                        f.write(json.dumps(out_obj))
                return returnData
            finally:
                f=open(filename,'r')
                return f.read()
        elif str(filePath).split('.')[-1]=="mp3":
            patient_report = extract_audio_text(f"{file.parent}/{file.name}")
            with open(extracted_filename,"w") as f:
                f.write(patient_report)
                print("written extracted text to file")
            prompt = "provide the summary of the below report \n"+patient_report
            response = model.generate_content(prompt)
            input_tokens = response.usage_metadata.prompt_token_count 
            output_tokens = response.usage_metadata.candidates_token_count
            out_obj = {"input_tokens":input_tokens,"output_tokens":output_tokens,"text":""}
            try:
                returnData = response.candidates[0].content.parts[0].text
                if returnData:
                    out_obj["text"] = returnData
                    with open(filename,"w") as f:
                        f.write(json.dumps(out_obj))
                        print("written to text file")
                return returnData
            except:
                returnData = response.text
                if returnData:
                    out_obj["text"] = returnData
                    with open(filename,"w") as f:
                        f.write(json.dumps(out_obj))
                        print("written to text file")
                return returnData
            finally:
                f=open(filename,'r')
                return f.read()
        elif str(filePath).split('.')[-1]=="mp4":
            patient_report = extract_video_text(f"{file.parent}/{file.name}")
            with open(extracted_filename,"w") as f:
                f.write(patient_report)
                print("written extracted text to file")
            prompt = "provide the summary of the below report \n"+patient_report
            response = model.generate_content(prompt)
            input_tokens = response.usage_metadata.prompt_token_count 
            output_tokens = response.usage_metadata.candidates_token_count
            out_obj = {"input_tokens":input_tokens,"output_tokens":output_tokens,"text":""}
            try:
                returnData = response.candidates[0].content.parts[0].text
                if returnData:
                    out_obj["text"] = returnData
                    with open(filename,"w") as f:
                        f.write(json.dumps(out_obj))
                        print("written to text file")
                return returnData
            except:
                returnData = response.text
                if returnData:
                    out_obj["text"] = returnData
                    with open(filename,"w") as f:
                        f.write(json.dumps(out_obj))
                        print("written to text file")
                return returnData
            finally:
                f=open(filename,'r')
                return f.read()
    except Exception as e:
        print("Error:"+filePath,e)
        return "Some error occured"

# @app.route("/gemini_multimodal_summary")
def gemini_multimodal_aifeature(filePath,aifeature,workspace_path):
    # dbParams = json.loads(request.args.get("dbParams"))
    # filePath = dbParams['selectedFile']
    print("Entered multimodal ai feature "+aifeature+" for file "+filePath)
    fileAbs = Path(filePath);
    file = Path(workspace_path+"/"+filePath)
    print(filePath)
    filename = f"static/OutputCache/{aifeature}/{fileAbs.parent}/{fileAbs.stem}.txt"
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    extracted_filename = f"static/OutputCache/Extracted/{fileAbs.parent}/{fileAbs.stem}.txt"

    #entity = str(filePath).split('/')[0]
    try:
        generation_config = {
            "temperature":0.9,
            "top_p":1,
            "top_k":0,
            "max_output_tokens":4096
        }
        safety_settings = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
        },
        ]
        model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest",
                                            generation_config=generation_config,
                                            safety_settings=safety_settings)
        if str(filePath).split('.')[-1]=="pdf":
            f=open(extracted_filename,'r')
            patient_report = f.read()
            prompt = ""
            if aifeature == "Sentiment":
                prompt = "provide the sentiment of  below report in any of the below options: Positive,Negative,Neutral. Return answer in form of json with key as Sentiment and value from given options.\n\n"+patient_report
            elif aifeature == "Emotion":
                prompt = "Predict the emotion based on report from provided options : [ 'Happiness', 'Sadness', 'Anger', 'Fear', 'Suprise', 'Disgust']. Return answer in form of json with key as Emotion and value from given options.\n\n"+patient_report
            elif aifeature == "Tone":
                prompt = "Predict the Tone based on report from provided options : [ 'FORMAL', 'INFORMAL', 'OPTIMISTIC', 'HARSH']. Return answer in form of json with key as Tone and value from given options.\n\n"+patient_report
            elif aifeature == "EnglishMaturity":
                prompt = "Predict the English Maturity of the report from provided options : [ 'AVERAGE', 'MEDIUM', 'PROFICIENT', 'LOW']. Return answer in form of json with key as EnglishMaturity and value from given options.\n\n" + patient_report
            response = model.generate_content(prompt)
            try:
                returnData = response.candidates[0].content.parts[0].text
                if returnData:
                    with open(filename,"w") as f:
                        f.write(returnData)
                        print("written to text file")
                return returnData
            except:
                returnData = response.text
                if returnData:
                    with open(filename, 'w') as f:
                        f.write(returnData)
                        print("written to text file")
                return returnData
            finally:
                f=open(filename,'r')
                return f.read()
        elif str(filePath).split('.')[-1]=="png" or filePath.split('.')[-1]=="jpeg" or filePath.split('.')[-1]=="jpg":
            try:
                user_prompt = ""
                image_parts = [
                    {
                        "mime_type": "image/jpeg", ## Mime type are PNG - image/png. JPEG - image/jpeg. WEBP - image/webp
                        "data": file.read_bytes()
                    }
                ]
                system_prompt = """
                        You are a radiologist expert in interpreting MRI scanning reports and identifies abnormalities to provide accurate diagnoses..
                        Input images in the form of MRI sacnning images  will be provided to you,
                        and your task is to respond to questions based on the image.
                        """
                if aifeature == "Sentiment":
                    user_prompt = "provide the sentiment of  image in any of the below options: Positive,Negative,Neutral. Return answer in form of json with key as Sentiment and value from given options.\n\n"
                elif aifeature == "Emotion":
                    user_prompt = "Predict the emotion based on report from provided options : [ 'Happiness', 'Sadness', 'Anger', 'Fear', 'Suprise', 'Disgust']. Return answer in form of json with key as Emotion and value from given options.\n\n"
                elif aifeature == "Tone":
                    user_prompt = "Predict the Tone based on report from provided options : [ 'FORMAL', 'INFORMAL', 'OPTIMISTIC', 'HARSH']. Return answer in form of json with key as Tone and value from given options.\n\n"
                elif aifeature == "EnglishMaturity":
                    user_prompt = "Predict the English Maturity of the report from provided options : [ 'AVERAGE', 'MEDIUM', 'PROFICIENT', 'LOW']. Return answer in form of json with key as EnglishMaturity and value from given options.\n\n"
            
                input_prompt= [system_prompt, image_parts[0], user_prompt]
                response = model.generate_content(input_prompt)
                returnData = response.Candidates[0].content.parts[0].text
                if returnData:
                    with open(filename,'w') as f:
                        f.write(returnData)
                return returnData
            except:
                returnData = response.text
                if returnData:
                    with open(filename,'w') as f:
                        f.write(returnData)
                return returnData
            finally:
                f=open(filename,'r')
                return f.read() 
        elif str(filePath).split('.')[-1]=="mp3":
            f=open(extracted_filename,'r')
            patient_report = f.read()
            prompt = ""
            if aifeature == "Sentiment":
                prompt = "provide the sentiment of  below report in any of the below options: Positive,Negative,Neutral. Return answer in form of json with key as Sentiment and value from given options.\n\n"+patient_report
            elif aifeature == "Emotion":
                prompt = "Predict the emotion based on report from provided options : [ 'Happiness', 'Sadness', 'Anger', 'Fear', 'Suprise', 'Disgust']. Return answer in form of json with key as Emotion and value from given options.\n\n"+patient_report
            elif aifeature == "Tone":
                prompt = "Predict the Tone based on report from provided options : [ 'FORMAL', 'INFORMAL', 'OPTIMISTIC', 'HARSH']. Return answer in form of json with key as Tone and value from given options.\n\n"+patient_report
            elif aifeature == "EnglishMaturity":
                prompt = "Predict the English Maturity of the report from provided options : [ 'AVERAGE', 'MEDIUM', 'PROFICIENT', 'LOW']. Return answer in form of json with key as EnglishMaturity and value from given options.\n\n" + patient_report
            response = model.generate_content(prompt)
            try:
                returnData = response.candidates[0].content.parts[0].text
                if returnData:
                    with open(filename,"w") as f:
                        f.write(returnData)
                        print("written to text file")
                return returnData
            except:
                returnData = response.text
                if returnData:
                    with open(filename, 'w') as f:
                        f.write(returnData)
                        print("written to text file")
                return returnData
            finally:
                f=open(filename,'r')
                return f.read()
        elif str(filePath).split('.')[-1]=="mp4":
            f=open(extracted_filename,'r')
            patient_report = f.read()
            prompt = ""
            if aifeature == "Sentiment":
                prompt = "provide the sentiment of  below report in any of the below options: Positive,Negative,Neutral. Return answer in form of json with key as Sentiment and value from given options.\n\n"+patient_report
            elif aifeature == "Emotion":
                prompt = "Predict the emotion based on report from provided options : [ 'Happiness', 'Sadness', 'Anger', 'Fear', 'Suprise', 'Disgust']. Return answer in form of json with key as Emotion and value from given options.\n\n"+patient_report
            elif aifeature == "Tone":
                prompt = "Predict the Tone based on report from provided options : [ 'FORMAL', 'INFORMAL', 'OPTIMISTIC', 'HARSH']. Return answer in form of json with key as Tone and value from given options.\n\n"+patient_report
            elif aifeature == "EnglishMaturity":
                prompt = "Predict the English Maturity of the report from provided options : [ 'AVERAGE', 'MEDIUM', 'PROFICIENT', 'LOW']. Return answer in form of json with key as EnglishMaturity and value from given options.\n\n" + patient_report
            response = model.generate_content(prompt)
            try:
                returnData = response.candidates[0].content.parts[0].text
                if returnData:
                    with open(filename,"w") as f:
                        f.write(returnData)
                        print("written to text file")
                return returnData
            except:
                returnData = response.text
                if returnData:
                    with open(filename, 'w') as f:
                        f.write(returnData)
                        print("written to text file")
                return returnData
            finally:
                f=open(filename,'r')
                return f.read()
    except Exception as e:
        print("Error:"+filePath,e)
        return "Some error occured"
    
def get_access_token():
    # Load Google Playground credentials from environment variables
    client_id = os.getenv("GOOGLE_CLIENT_ID")

    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
   
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
   

    # Make a request to the Google OAuth 2.0 token endpoint to get a new access token
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token
    }
    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        access_token = response.json().get("access_token")
        return access_token
    else:
        print(f"Error fetching access token: {response.status_code}, {response.text}")
        return None


def update_dates(data):
    new_data = {}
    for category, values in data.items():
        new_data[category] = []
        new_json = {}
        current_date = datetime.now().strftime("%Y-%m-%d")
        previous_date = None
        
        for date, value in reversed(values[0].items()):
            if previous_date is None:
                previous_date = datetime.strptime(current_date, "%Y-%m-%d")
                new_json[current_date] = value
            else:
                previous_date = previous_date - timedelta(days=1)
                new_json[previous_date.strftime("%Y-%m-%d")] = value
        
        new_data[category].append(new_json)
    
    return new_data

@app.route("/get_google_fit_data_old")
def google_fit_data_old():
    try:
        # ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
        ACCESS_TOKEN = "ya29.a0AXooCgsw-RXQOmz73-e35V6dd7JtjrsiS2wZuDd-wnCrdApgnCoISpNjy5nDFrXhMf3aUoiMEcKfZt9IyntKm1ZZId2VbCat91MsBYK5QfKxo8znkCFYcyNjNGV6wtblHrX0Pl93G0gHFK_up6f_XNrFIGTtEugHpaCgYKARcSARASFQHGX2MikwDwTPfwHGEcuhQNkqL_kw0171"
        # Base URL for Google Fit API
        # ACCESS_TOKEN = get_access_token()
        print("Access token:", ACCESS_TOKEN)
        if ACCESS_TOKEN is None:
            return
        base_url = "https://www.googleapis.com/fitness/v1/users/me"
        headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
        # Adjust for desired start and end times for the last 10 days
        end_time = datetime.now()
        start_time = end_time - timedelta(days=10)
        start_time_ns = int(time.mktime(start_time.timetuple()) * 1e9)
        end_time_ns = int(time.mktime(end_time.timetuple()) * 1e9)
        
        # Replace with your specific data source ID for Heart Points
        data_source_id = 'derived:com.google.heart_minutes:com.google.android.gms:merge_heart_minutes'

        # Construct dataset ID
        dataset_id = f"{start_time_ns}-{end_time_ns}"
        dataset_url = f"{base_url}/dataSources/{data_source_id}/datasets/{dataset_id}"
        # print(dataset_url)

        # Retrieve data
        response = requests.get(dataset_url, headers=headers)
        

        if response.status_code == 200:
            dataset = response.json()
            heart_points_by_date = defaultdict(float)
            
            for point in dataset.get("point", []):
                start_time_ns = int(point["startTimeNanos"])
                date = datetime.fromtimestamp(start_time_ns / 1e9).date().isoformat()
                for value in point.get("value", []):
                    heart_points_by_date[date] += value.get("fpVal", 0)
            
            heart_points_json = dict(heart_points_by_date)
            # print(heart_points_json)
        else:
            print(f"Error retrieving data: {response.status_code}, {response.text}")
        
        # Adjust for desired start and end times for the last 10 days
        end_time = datetime.now()
        start_time = end_time - timedelta(days=10)
        start_time_ns = int(time.mktime(start_time.timetuple()) * 1e9)
        end_time_ns = int(time.mktime(end_time.timetuple()) * 1e9)
        # Replace with your specific data source ID for Step Count
        data_source_id = 'derived:com.google.step_count.delta:com.google.android.gms:merge_step_deltas'

        # Construct dataset ID
        dataset_id = f"{start_time_ns}-{end_time_ns}"
        dataset_url = f"{base_url}/dataSources/{data_source_id}/datasets/{dataset_id}"
        # print(dataset_url)

        # Retrieve data
        response = requests.get(dataset_url, headers=headers)

        if response.status_code == 200:
            dataset = response.json()
            steps_by_date = defaultdict(int)
            
            for point in dataset.get("point", []):
                start_time_ns = int(point["startTimeNanos"])
                # date = from_nanoseconds(start_time_ns).date().isoformat()
                date = datetime.fromtimestamp(start_time_ns / 1e9).date().isoformat()
                for value in point.get("value", []):
                    steps_by_date[date] += value.get("intVal", 0)
            
            steps_json = dict(steps_by_date)
            # print(steps_json)
        else:
            print(f"Error retrieving data: {response.status_code}, {response.text}")
        
        # Adjust for desired start and end times for the last 10 days
        end_time = datetime.now()
        start_time = end_time - timedelta(days=10)
        start_time_ns = int(time.mktime(start_time.timetuple()) * 1e9)
        end_time_ns = int(time.mktime(end_time.timetuple()) * 1e9)
        # Replace with your specific data source ID for Calories Burned
        data_source_id = 'derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended'

        # Construct dataset ID
        dataset_id = f"{start_time_ns}-{end_time_ns}"
        dataset_url = f"{base_url}/dataSources/{data_source_id}/datasets/{dataset_id}"
        # print(dataset_url)

        # Retrieve data
        response = requests.get(dataset_url, headers=headers)

        if response.status_code == 200:
            dataset = response.json()
            calories_by_date = defaultdict(float)
            
            for point in dataset.get("point", []):
                start_time_ns = int(point["startTimeNanos"])
                # date = from_nanoseconds(start_time_ns).date().isoformat()
                date =datetime.fromtimestamp(start_time_ns / 1e9).date().isoformat()
                for value in point.get("value", []):
                    calories_by_date[date] += value.get("fpVal", 0)
            
            calories_json = dict(calories_by_date)
            # print(calories_json)
        else:
            print(f"Error retrieving data: {response.status_code}, {response.text}")
        data = {"Heartpoints": [heart_points_json], "StepCount":[steps_json], "CaloriesBurned":[calories_json]}
        new_data = {}
        for key, value in data.items():
            new_data[key] = []
            for item in value:
                for date, val in item.items():
                    new_data[key].append({"date": date, "value": round(val, 2)})
        with open('static/OutputCache/google_fit_cache.json', 'w') as f:
            json.dump(data, f)
        print(json.dumps(new_data))
        return new_data
    except Exception as e:
        print(e)
        if os.path.exists('static/OutputCache/google_fit_cache.json'):
            with open('static/OutputCache/google_fit_cache.json', 'r') as f:
                data =  json.load(f)
            shifted_data = update_dates(data)
            new_data = {}
            for key, value in shifted_data.items():
                new_data[key] = []
                for item in value:
                    for date, val in item.items():
                        new_data[key].append({"date": date, "value": round(val, 2)})
            return new_data
        return None

def update_dates(data):
    new_data = {}
    for category, values in data.items():
        new_data[category] = []
        new_json = {}
        current_date = datetime.now().strftime("%Y-%m-%d")
        previous_date = None

        for date, value in reversed(values[0].items()):
            if previous_date is None:
                previous_date = datetime.strptime(current_date, "%Y-%m-%d")
                new_json[current_date] = value
            else:
                previous_date = previous_date - timedelta(days=1)
                new_json[previous_date.strftime("%Y-%m-%d")] = value

        new_data[category].append(new_json)

    return new_data

def get_heart_points(heart_points: str) -> str:
    """Fetches the Heart points for last 10 days from google fit API."""
    try:
        # ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
        ACCESS_TOKEN = "ya29.a0AXooCgv81bpH63OAy6-xuMAnIx0DTQTmS27HkaZjB3ITW1bYZAqeHMxzYKwZJa3g5HMzveyrJ9xfaI5GO7E4bLdpgZMamDPGnTXBDOd-wq3Lxh5fvuCvpOdrJD37Z3auwQV7cHiMVOCbznQ8DfiE_fosk7I02-728fJ7aCgYKASkSARASFQHGX2Mik8uAsJ3mL0eD3Ns8u9EgVg0171"
        # Base URL for Google Fit API
        # ACCESS_TOKEN = get_access_token()
        print("Access token:", ACCESS_TOKEN)
        if ACCESS_TOKEN is None:
            return
        base_url = "https://www.googleapis.com/fitness/v1/users/me"
        headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
        # Adjust for desired start and end times for the last 10 days
        end_time = datetime.now()
        start_time = end_time - timedelta(days=10)
        start_time_ns = int(time.mktime(start_time.timetuple()) * 1e9)
        end_time_ns = int(time.mktime(end_time.timetuple()) * 1e9)

        # Replace with your specific data source ID for Heart Points
        data_source_id = 'derived:com.google.heart_minutes:com.google.android.gms:merge_heart_minutes'

        # Construct dataset ID
        dataset_id = f"{start_time_ns}-{end_time_ns}"
        dataset_url = f"{base_url}/dataSources/{data_source_id}/datasets/{dataset_id}"
        # print(dataset_url)

        # Retrieve data
        response = requests.get(dataset_url, headers=headers)


        if response.status_code == 200:
            dataset = response.json()
            heart_points_by_date = defaultdict(float)

            for point in dataset.get("point", []):
                start_time_ns = int(point["startTimeNanos"])
                date = datetime.fromtimestamp(start_time_ns / 1e9).date().isoformat()
                for value in point.get("value", []):
                    heart_points_by_date[date] += value.get("fpVal", 0)

            heart_points_json = dict(heart_points_by_date)
            # print(heart_points_json)
            data = {"Heartpoints": [heart_points_json]}
            new_data = {}
            for key, value in data.items():
                new_data[key] = []
                for item in value:
                    for date, val in item.items():
                        new_data[key].append({"date": date, "value": round(val, 2)})
            with open('static/OutputCache/google_fit_heartpoints.json', 'w') as f:
                json.dump(data, f)
            print(json.dumps(new_data))
            return new_data
        else:
            if os.path.exists('static/OutputCache/google_fit_heartpoints.json'):
                with open('static/OutputCache/google_fit_heartpoints.json', 'r') as f:
                    data =  json.load(f)
                shifted_data = update_dates(data)
                new_data = {}
                for key, value in shifted_data.items():
                    new_data[key] = []
                    for item in value:
                        for date, val in item.items():
                            new_data[key].append({"date": date, "value": round(val, 2)})
                print("heart points", new_data)
                return new_data
            else:
                return "Error retrieving data"
    except Exception as e:
        print(e)
        if os.path.exists('static/OutputCache/google_fit_heartpoints.json'):
            with open('static/OutputCache/google_fit_heartpoints.json', 'r') as f:
                data =  json.load(f)
            shifted_data = update_dates(data)
            new_data = {}
            for key, value in shifted_data.items():
                new_data[key] = []
                for item in value:
                    for date, val in item.items():
                        new_data[key].append({"date": date, "value": round(val, 2)})
            print("heart points", new_data)
            return new_data
        else:
            return "Error retrieving data"

def get_steps(steps: str, reason: str) -> str:
    """Fetches the steps count for last 10 days from google fit API."""
    try:
        # ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
        ACCESS_TOKEN = "ya29.a0AXooCgv81bpH63OAy6-xuMAnIx0DTQTmS27HkaZjB3ITW1bYZAqeHMxzYKwZJa3g5HMzveyrJ9xfaI5GO7E4bLdpgZMamDPGnTXBDOd-wq3Lxh5fvuCvpOdrJD37Z3auwQV7cHiMVOCbznQ8DfiE_fosk7I02-728fJ7aCgYKASkSARASFQHGX2Mik8uAsJ3mL0eD3Ns8u9EgVg0171"
        # Base URL for Google Fit API
        # ACCESS_TOKEN = get_access_token()
        print("Access token:", ACCESS_TOKEN)
        if ACCESS_TOKEN is None:
            return
        base_url = "https://www.googleapis.com/fitness/v1/users/me"
        headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
        # Adjust for desired start and end times for the last 10 days
        end_time = datetime.now()
        start_time = end_time - timedelta(days=10)
        start_time_ns = int(time.mktime(start_time.timetuple()) * 1e9)
        end_time_ns = int(time.mktime(end_time.timetuple()) * 1e9)

        # Replace with your specific data source ID for Step Count
        data_source_id = 'derived:com.google.step_count.delta:com.google.android.gms:merge_step_deltas'

        # Construct dataset ID
        dataset_id = f"{start_time_ns}-{end_time_ns}"
        dataset_url = f"{base_url}/dataSources/{data_source_id}/datasets/{dataset_id}"
        # print(dataset_url)

        # Retrieve data
        response = requests.get(dataset_url, headers=headers)

        if response.status_code == 200:
            dataset = response.json()
            steps_by_date = defaultdict(int)

            for point in dataset.get("point", []):
                start_time_ns = int(point["startTimeNanos"])
                # date = from_nanoseconds(start_time_ns).date().isoformat()
                date = datetime.fromtimestamp(start_time_ns / 1e9).date().isoformat()
                for value in point.get("value", []):
                    steps_by_date[date] += value.get("intVal", 0)

            steps_json = dict(steps_by_date)
            # print(steps_json)
            data = {"Steps": [steps_json]}
            new_data = {}
            for key, value in data.items():
                new_data[key] = []
                for item in value:
                    for date, val in item.items():
                        new_data[key].append({"date": date, "value": round(val, 2)})
            with open('static/OutputCache/google_fit_steps.json', 'w') as f:
                json.dump(data, f)
            print(json.dumps(new_data))
            return new_data
        else:
            if os.path.exists('static/OutputCache/google_fit_steps.json'):
                with open('static/OutputCache/google_fit_steps.json', 'r') as f:
                    data =  json.load(f)
                shifted_data = update_dates(data)
                new_data = {}
                for key, value in shifted_data.items():
                    new_data[key] = []
                    for item in value:
                        for date, val in item.items():
                            new_data[key].append({"date": date, "value": round(val, 2)})
                return new_data
            else:
                return "Error retrieving data"
    except Exception as e:
        print(e)
        if os.path.exists('static/OutputCache/google_fit_steps.json'):
            with open('static/OutputCache/google_fit_steps.json', 'r') as f:
                data =  json.load(f)
            shifted_data = update_dates(data)
            new_data = {}
            for key, value in shifted_data.items():
                new_data[key] = []
                for item in value:
                    for date, val in item.items():
                        new_data[key].append({"date": date, "value": round(val, 2)})
            return new_data
        else:
            return "Error retrieving data"

def get_calories(calories: str, reason: str) -> str:
    """Fetches the calories burned for last 10 days from google fit API."""
    try:
        # ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
        ACCESS_TOKEN = "ya29.a0AXooCgv81bpH63OAy6-xuMAnIx0DTQTmS27HkaZjB3ITW1bYZAqeHMxzYKwZJa3g5HMzveyrJ9xfaI5GO7E4bLdpgZMamDPGnTXBDOd-wq3Lxh5fvuCvpOdrJD37Z3auwQV7cHiMVOCbznQ8DfiE_fosk7I02-728fJ7aCgYKASkSARASFQHGX2Mik8uAsJ3mL0eD3Ns8u9EgVg0171"
        # Base URL for Google Fit API
        # ACCESS_TOKEN = get_access_token()
        print("Access token:", ACCESS_TOKEN)
        if ACCESS_TOKEN is None:
            return
        base_url = "https://www.googleapis.com/fitness/v1/users/me"
        headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
        # Adjust for desired start and end times for the last 10 days
        end_time = datetime.now()
        start_time = end_time - timedelta(days=10)
        start_time_ns = int(time.mktime(start_time.timetuple()) * 1e9)
        end_time_ns = int(time.mktime(end_time.timetuple()) * 1e9)

         # Replace with your specific data source ID for Calories Burned
        data_source_id = 'derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended'

        # Construct dataset ID
        dataset_id = f"{start_time_ns}-{end_time_ns}"
        dataset_url = f"{base_url}/dataSources/{data_source_id}/datasets/{dataset_id}"
        # print(dataset_url)

        # Retrieve data
        response = requests.get(dataset_url, headers=headers)

        if response.status_code == 200:
            dataset = response.json()
            calories_by_date = defaultdict(float)

            for point in dataset.get("point", []):
                start_time_ns = int(point["startTimeNanos"])
                # date = from_nanoseconds(start_time_ns).date().isoformat()
                date =datetime.fromtimestamp(start_time_ns / 1e9).date().isoformat()
                for value in point.get("value", []):
                    calories_by_date[date] += value.get("fpVal", 0)

            calories_json = dict(calories_by_date)
            # print(calories_json)
            data = {"CaloriesBurned": [calories_json]}
            new_data = {}
            for key, value in data.items():
                new_data[key] = []
                for item in value:
                    for date, val in item.items():
                        new_data[key].append({"date": date, "value": round(val, 2)})
            with open('static/OutputCache/google_fit_calories.json', 'w') as f:
                json.dump(data, f)
            print(json.dumps(new_data))
            return new_data
        else:
            if os.path.exists('static/OutputCache/google_fit_calories.json'):
                with open('static/OutputCache/google_fit_calories.json', 'r') as f:
                    data =  json.load(f)
                shifted_data = update_dates(data)
                new_data = {}
                for key, value in shifted_data.items():
                    new_data[key] = []
                    for item in value:
                        for date, val in item.items():
                            new_data[key].append({"date": date, "value": round(val, 2)})
                return new_data
            else:
                return "Error retrieving data"
    except Exception as e:
        print(e)
        if os.path.exists('static/OutputCache/google_fit_calories.json'):
            with open('static/OutputCache/google_fit_calories.json', 'r') as f:
                data =  json.load(f)
            shifted_data = update_dates(data)
            new_data = {}
            for key, value in shifted_data.items():
                new_data[key] = []
                for item in value:
                    for date, val in item.items():
                        new_data[key].append({"date": date, "value": round(val, 2)})
            return new_data
        else:
            return "Error retrieving data"

@app.route("/get_google_fit_data")  
@track_emissions(output_dir="static",project_name="Panacea")
def get_google_fit_data():
    chat_model = genai.GenerativeModel(
        model_name='gemini-1.5-flash-latest',
        tools=[get_heart_points, get_steps, get_calories] # list of all available tools
    )

    """### alway use the model in chat mode for function calling"""

    chat = chat_model.start_chat(enable_automatic_function_calling=True)


    response = chat.send_message('Give the heart points for the last 10 days. Return only function response without any additional text')
    heart_json = str(response.candidates[0].content.parts[0].text)

    response = chat.send_message('Give the steps count for the last 10 days')
    steps_json = str(response.candidates[0].content.parts[0].text)

    response = chat.send_message('Give the calories burned for the last 10 days')
    calories_json = str(response.candidates[0].content.parts[0].text)

    return {"heart_json":heart_json,"steps_json":steps_json,"calories_json":calories_json}

@app.route("/explain_fit_data")
@track_emissions(output_dir="static",project_name="Panacea")
def explain_fit_data():
    dbParams = json.loads(request.args.get("dbParams"))
    fit_json = dbParams['fitJson']
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = "Explain the condition of person or patient based on provided json data extracted from google fit.\n\n" + fit_json
    response = model.generate_content(prompt)
    cache_file_path = f"static/OutputCache/Gemini-FitData-Summary.txt"
    path = Path(cache_file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    print("gemini_fitdata_summary done")
    try:
        returnData = response.candidates[0].content.parts[0].text
        if len(returnData) > 10:
            f = open(cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.candidates[0].content.parts[0].text

    except:
        returnData = response.text
        if len(returnData) > 10:
            f = open(
                cache_file_path, "w", encoding='cp1252')
            f.write(returnData)
            f.close()
        return response.text
    finally:
        # open and read the file after the overwriting:
        f = open(
            cache_file_path, "r", encoding='cp1252')
        return f.read()

#@app.route("/get_opentext_auth_token",methods = ['GET'])
def get_opentext_auth_token():
    url = "https://us.api.opentext.com/tenants/6940d09e-0f19-4929-9618-724037d07bc3/oauth2/token"
    payload = 'grant_type=client_credentials&client_secret=encoded&client_id=encoded'
    headers = {
    'Authorization': 'Basic UDRtQW92RVJwdkFzMFUzR0k4UWlMODA5bWY4SzdaU2M6a2QxdVlXUTlXTlN0NDU2NA==',
    'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    response_data = response.json()
    token = response_data["access_token"]
    return token

@app.route("/get_opentext_auth_token_for_notifications",methods = ['GET'])
def get_opentext_auth_token_for_notifications():
    url = "https://us.api.opentext.com/tenants/6940d09e-0f19-4929-9618-724037d07bc3/oauth2/token"
    payload = 'grant_type=client_credentials&client_secret=encoded&client_id=encoded'
    headers = {
    'Authorization': 'Basic UDRtQW92RVJwdkFzMFUzR0k4UWlMODA5bWY4SzdaU2M6a2QxdVlXUTlXTlN0NDU2NA==',
    'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    response_data = response.json()
    token = response_data["access_token"]
    return response_data

@app.route("/get_opentext_auth_token_for_ocp",methods = ['GET'])
def get_opentext_auth_token_for_ocp():
    #First we're going to login to the OT2 authentication service
    print("Logging in to OT2")
    
    #This is the Autehntication URL
    #eu "https://otdsauth.ot2.opentext.eu/oauth2/token"
    authUrl = "https://us.api.opentext.com/tenants/6940d09e-0f19-4929-9618-724037d07bc3/oauth2/token"
    
    # authUrl = "https://otdsauth.ot2.opentext.com/oauth2/token"
    #Now create the Login request
    loginRequest = {}
    loginRequest['grant_type'] = 'client_credentials'
    loginRequest['username'] = 'dataflow.expedition@gmail.com'
    loginRequest['password'] = 'Infy1234567@'
    # loginRequest['subscriptionName'] = 'cap-69616598-1c0a-44b7-8ec7-8d0bf8edcffa-1017'
    
    #Take the client secret from the developer console and convert it to base 64
    client = 'P4mAovERpvAs0U3GI8QiL809mf8K7ZSc'
    secret = 'kd1uYWQ9WNSt4564'

    # client = '905a0aff-b691-47e2-a655-51d2f9573856'
    # secret = '6634a87c7a88452cb7e3e7ec08102a88'
    clientSecret = client + ':' + secret
    csEncoded = base64.b64encode(clientSecret.encode())
    
    # You now need to decode the Base64 to a string version
    csString = csEncoded.decode('utf-8')
    
    #Add the Client Secret and content Type to the request header
    loginHeaders={}
    loginHeaders['Content-Type'] = 'application/x-www-form-urlencoded'
    loginHeaders['Authorization'] = "Basic " + csString
    
    #Now post the request
    r = requests.post(authUrl,data=loginRequest,headers=loginHeaders)
    loginResponse = json.loads(r.text)
    
    #Get the Access Token from the request
    accessToken = loginResponse['access_token']
    return accessToken


@app.route("/get_list_ocr",methods = ["GET"])
def get_list_ocr():
    # baseURL = 'https://capture.ot2.opentext.com/cp-rest/session'
    accessToken = get_opentext_auth_token()
    serviceHeaders = {}
    serviceHeaders['Authorization'] = 'Bearer ' + accessToken
    serviceHeaders['Content-Type'] = 'application/hal+json; charset=utf-8'
    baseURL = 'https://us.api.opentext.com/capture/cp-rest/v2'
    #Now for the file resource
    uploadURL = baseURL + '/session/doctypes?Env=D'
    
    uploadRequest = requests.get(uploadURL,headers=serviceHeaders)
    res = json.loads(uploadRequest.text)
    return res

# @app.route("/get_token_for_signature_ocp",methods = ['GET'])
def get_token_for_signature_ocp():
    url = "https://us.api.opentext.com/tenants/a9421ab6-5963-4882-bdf7-df3b0bad9546/oauth2/token"

    payload = 'grant_type=client_credentials&client_secret=encoded&client_id=encoded'
    # client_id : vrwul1CkK652Jd64RKRkhXgz2IWajU18
    # secret : Fc1Qx1sZ6y209JLj
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': 'Basic dnJ3dWwxQ2tLNjUySmQ2NFJLUmtoWGd6MklXYWpVMTg6RmMxUXgxc1o2eTIwOUpMag=='
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    response_data = response.json()
    return response_data["access_token"]

@app.route("/get_prescriptions",methods=["GET"])
def get_prescriptions():
    with open('static/Prescriptions.json', 'r') as f:
        prescription_data =  json.load(f)
    return prescription_data


@app.route("/create_document_sign_ocp",methods=["GET"])
@track_emissions(output_dir="static",project_name="Panacea")
def create_document_sign_ocp():
    dbParams = json.loads(request.args.get("dbParams"))
    doctor_mail = dbParams['doctorMail']
    doctor_name = dbParams['doctorName']
    patient_mail = dbParams['patientMail']
    patient_name = dbParams['selectedPatient']
    prescription_id = dbParams['prescriptionId']
    prescription_subject = dbParams['prescriptionSubject']
    prescription_message = dbParams["prescriptionMessage"]
    prescription_text = dbParams["prescriptionText"]
    visited_date = dbParams["visitedDate"]
    file = "static/temp/Prescription.txt"
    with open(file, 'w') as f:
        f.write(prescription_text)
    token = get_token_for_signature_ocp()
    url = "https://sign.core.opentext.com/api/v1/signature-request-quick-create/"
    summary_content = open(file,'rb').read()
    # summary_content = prescription_text
    summary_b64 = base64.encodebytes(summary_content)
    summary_b64_str = summary_b64.decode('utf-8')
    
    payload = json.dumps({
        "from_email_name":doctor_name,
        "is_being_prepared": False,
        "subject": prescription_subject,
        "message": prescription_message,
        "who": "o",
        "signers": [
            {
                "email": doctor_mail,
                "order": "1",
                "full_name":doctor_name
            },
            {
                "email": patient_mail,
                "order": "2",
                "full_name":patient_name
            }
        ],
        "name": patient_name+" Prescription-"+str(prescription_id),
        "file_from_content": summary_b64_str,
        "file_from_content_name": patient_name+"  Prescription-"+str(prescription_id)+".txt",
        "auto_expire_days": 5
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer '+token,
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    sign_response = response.json()
    print(sign_response)
    document = {"document":sign_response["document"],"name":sign_response["name"],"doctor":sign_response["signers"][1]["full_name"],"visited":visited_date}
    with open('static/Prescriptions.json', 'r') as f:
        prescription_data =  json.load(f)
    prescription_data.append(document)
    with open('static/Prescriptions.json', 'w') as f:
            json.dump(prescription_data, f)
    return document

@app.route("/retrieve_doc_ocp",methods=["GET"])
@track_emissions(output_dir="static",project_name="Panacea")
def retrieve_doc_ocp():
    dbParams = json.loads(request.args.get("dbParams"))
    document = dbParams['document']
    token = get_token_for_signature_ocp()
    payload = {}
    headers = {
    'Authorization': 'Bearer '+token    
    }
    response = requests.request("GET", document, headers=headers, data=payload)
    data = response.json()
    print(data)
    return data["pdf"]

@app.route("/upload_file_css_ocp",methods=["GET"])
def upload_file_css_ocp():
    file = "static/OutputCache/Gemini-SummaryContent-AmyCripto.txt"
    token = get_opentext_auth_token()
    url = "https://css.us.api.opentext.com/v2/content"
    payload = {}
    headers = {
        'Authorization': 'Bearer '+token
    }
    with open(file, 'rb') as fobj:
        upload_response = requests.request("POST", url, headers=headers, files={"File":fobj})
    upload_response = upload_response.json()
    upload_id = upload_response["entries"][0]["id"]
    # shareable_link_url = "https://css.us.api.opentext.com/v2/content/"+upload_id+"/publicShareUrl"
    # share_payload = json.dumps({
    # "password": "Infy123",
    # })
    # share_headers = {
    #     'Authorization': 'Bearer '+token,
    #     'Content-Type': 'application/json',
    #     'Accept': 'application/json'    
    # }
    # response = requests.request("POST", shareable_link_url, headers=headers, data=share_payload)
    return upload_response

@app.route("/upload_file_css_ocp_v3",methods=["GET"])
def upload_file_css_ocp_v3():
    dbParams = json.loads(request.args.get("dbParams"))
    filePath = dbParams['selectedFile']
    userName = dbParams['userName']
    wspName = dbParams['wspName']
    file_path = workspace_dir_path+'/'+filePath
    token = get_opentext_auth_token()
    url = "https://css.us.api.opentext.com/v3/files/fromStream"
    payload = {}
    headers = {
        'Authorization': 'Bearer '+token
    }
    with open(file_path, 'rb') as fobj:
        upload_response = requests.request("POST", url, headers=headers, files={"File":fobj})
    upload_response = upload_response.json()
    return upload_response

@app.route("/create_cms_file_instance_ocp",methods=["GET"])
def create_cms_file_instance_ocp():
    url = "https://us.api.opentext.com/cms/instances/file/"

    payload = json.dumps({
    "name": "Training SOP 1724254791",
    "description": "Code Conduct training",
    "version_label": [
        "first"
    ],
    "properties": {
        "classification": "Internal",
        "department_name": "R&D",
        "status": "Draft"
    },
    "renditions": [
        {
        "name": "my content file",
        "rendition_type": "primary",
        "blob_id": "https://css.us.api.opentext.com/v2/content/cj04NjAxODU1ZC1jMjg4LTQ5NzUtYjBhNC04MjhiOGQ3YzM4OGQmaT04M2IxZWI5OS0yN2Q3LTRmOTUtODhhZC0xNjc5ZTQzNDM1MDI=/download"
        }
    ]
    })
    headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer eyJraWQiOiIyMTRmODE5ZWQ5M2I3Yzg3N2U1OWEwMGQ3YzUwODQ5YWI3Yjc4Y2Y1IiwidHlwIjoiYXQrand0IiwiYWxnIjoiUlMyNTYifQ.eyJ0ZW5hbnRfaWQiOiI2OTQwZDA5ZS0wZjE5LTQ5MjktOTYxOC03MjQwMzdkMDdiYzMiLCJzdWIiOiJmNDhmNWE3Mi00ZDcyLTRkOTUtOWVkMS0wY2UzNzE1NzA4OWEiLCJjb250cmFjdF9pZCI6IjkwNzMxY2UxLTY1NmMtNGRkMS04NWY4LWQ4OTkyZGNkMDcyYSIsImFtciI6W10sImlzcyI6Imh0dHBzOi8vY29tbW9uYXV0aC51cy5vcGVudGV4dC5jb20iLCJncnQiOiJjbGllbnRfY3JlZGVudGlhbHMiLCJzdWJfdHlwIjoxLCJjbGllbnRfaWQiOiJQNG1Bb3ZFUnB2QXMwVTNHSThRaUw4MDltZjhLN1pTYyIsInNpZCI6IjQ4MWUyMDJmLWFkNzctNDRiOS1hZTllLTlhNjYxNDgzODMxZCIsImF1ZCI6WyJzaWduIiwib3QyIl0sImF1dGhfdGltZSI6MTcyNDIyMDI0Mywic2NvcGUiOlsib3QyOmNyZWF0ZV9wdWJsaWNhdGlvbnMiLCJvdDI6ZGVsZXRlX3B1YmxpY2F0aW9ucyIsIm90Mjp2aWV3X3B1YmxpY2F0aW9ucyIsIm90MjpzZWFyY2hfcHVibGljYXRpb25zIiwib3QyOnJlYWR3cml0ZSIsIm90MjpzZWFyY2giXSwibmFtZSI6IlA0bUFvdkVScHZBczBVM0dJOFFpTDgwOW1mOEs3WlNjIiwiZXhwIjoxNzI0MjIxMTQzLCJpYXQiOjE3MjQyMjAyNDMsImp0aSI6IjhkZDFhMWVjLTZlNDEtNDdhOS1iNjc4LTNmOGNhN2FmNDA2YyJ9.AINX9wziYQJJ1vmf8O4Vk-2OQIR6hchmIPYem5GdBcwaHHQI-aMnzmLvsPwqz7MszoLbe7wQYK8QyuUAwfjpZQRGP_1HNisscYDlXluVOpAbHjJA9ztuHw_dduRyhUeY7LxmzAx8Ri3v06UzY5h0Mo7JvpFp5qNqrj_U8BsUWmN9e7Xb06hi5SSutqyATyNl1IHaf0MOPn_txnfq7bwTxb36BL4Jp_xBgv3R4xd-1wuG84_llDiY0q52WF9VSFhPZ4trSlA3UFDKEp119SPyneysohwF670nLQjgYvFmDBQF6F2gcua_TSGSnd13Ly8QCf5NQdOvCl8Q7muLrk8Faw'
    }

    response = requests.request("POST", url, headers=headers, data=payload)


@app.route("/download_file_css_ocp_v3",methods=["GET"])
def download_file_css_ocp_v3():
    file_id = "f3ca53f7-c9e5-42bf-93d5-930d78a6a295"
    token = get_opentext_auth_token()
    url = "https://css.us.api.opentext.com/v3/files/"+file_id+"/stream"
    payload = {}
    headers = {
        'Authorization': 'Bearer '+token
    }
    response = requests.request("GET", url, headers=headers)
    with open('static/CSS/temp.pdf', 'wb') as f:
        f.write(response.text)
    return "true"


@app.route("/send_email_ocp",methods = ["GET"])
def send_email_ocp():
    token = get_opentext_auth_token()
    url = "https://t2api.us.cloudmessaging.opentext.com/mra/v1/outbound/emails"

    payload = json.dumps({
    "options": {
        "email_options": {
        "subject": "Test Email from my app"
        }
    },
    "destinations": [
        {
        "ref": "1",
        "email": "kattamrudula8@gmail.com"
        },
        {
        "ref": "2",
        "email": "kattamrudula@gmail.com"
        }
    ],
    "body": [
        {
        "name": "temp.txt",
        "type": "text",
        "charset": "ISO-8859-1",
        "data": "SGkgVGhlcmUsIFRoaXMgaXMgYSB0ZXN0IERvY3VtZW50Lg=="
        }
    ]
    })
    headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer '+token
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    return response.text
  
@app.route("/get_ocr_content",methods=["GET"])
@track_emissions(output_dir="static",project_name="Panacea")
def get_ocr_content(file):
    # dbParams = json.loads(request.args.get("dbParams"))
    # filePath = dbParams['selectedFile']
    # file = workspace_dir_path+"/"+filePath

    token = get_opentext_auth_token()
    base_url = "https://us.api.opentext.com/capture/cp-rest/v2/session"
    upload_url = base_url+"/files"
    #use this token in all future headers
    #Create the service headers
    serviceHeaders = {}
    serviceHeaders['Authorization'] = 'Bearer ' + token
    serviceHeaders['Content-Type'] = 'application/hal+json; charset=utf-8'
    print('Uploading pdf')
    pdfUpload = {}
    pdfFile = open(file,'rb').read()
    pdfB64 = base64.encodebytes(pdfFile)
    
    #Assign this string to a data element called data
    pdfUpload['data'] = pdfB64.decode('utf-8')
    
    #Now get the Mimetype of the file
    #add 0 to get ('image/tiff', None)
    mime = mimetypes.guess_type(file)[0]
    pdfUpload['contentType'] = mime
    #Now convert the object to json
    uploadJson = json.dumps(pdfUpload)
    
    uploadRequest = requests.post(upload_url,data=uploadJson,headers=serviceHeaders)
    print(uploadRequest.text)
    uploadResponse = json.loads(uploadRequest.text)
    
    #get the image id
    upload_file_id = uploadResponse['id']
    print("upload_file_id",upload_file_id)
    url = base_url+"/services/fullpageocr"
    ocr_payload = json.dumps(
    {
        "serviceProps": [
            {
            "name": "Env",
            "value": "D"
            },
            {
            "name": "OcrEngineName",
            "value": "Advanced"
            },
            {
            "name": "AutoRotate",
            "value": "False"
            },
            {
            "name": "Country",
            "value": "USA"
            },
            {
            "name": "ProcessingMode",
            "value": "VoteOcrAndEText"
            }
        ],
        "requestItems": [
            {
            "nodeId": 1,
            "values": [
                {
                    "name": "OutputType",
                    "value": "Text"
                },
                {
                    "name": "Version",
                    "value": "Pdf"
                },
                {
                    "name": "Compression",
                    "value": "None"
                },
                {
                    "name":"ImageSelection",
                    "value":"OriginalImage"
                }
            ],
            "files": [
                {
                    "name": "AmyCriptoReport",
                    "value": upload_file_id,
                    "contentType": "application/pdf",
                    "fileType": "pdf"
                }
            ]
        }]
    })
    ocr_headers = {
        'Content-Type': 'application/hal+json',
        'Authorization': 'Bearer '+token
    }
    ocr_response = requests.request("POST", url, headers=ocr_headers, data=ocr_payload)
    ocr_response_json = ocr_response.json()
    print("pdf ocr done")
    ocr_id = ocr_response_json["resultItems"][0]["files"][0]["value"]
    url = "https://us.api.opentext.com/capture/cp-rest/v2/session/files/"+ocr_id
    payload = {}
    headers = {
    'Authorization': 'Bearer '+token
    }
    response = requests.request("GET", url, headers=headers, data=payload)
    delete_files_url = "https://us.api.opentext.com/capture/cp-rest/v2/session/files?filter=*&suppress_response_codes=suppress_response_codes"
    delete_files_response = requests.request("DELETE", delete_files_url, headers=headers, data=payload)
    print("deleted file")
    delete_session_url = "https://us.api.opentext.com/capture/cp-rest/v2/session?suppress_response_codes=suppress_response_codes"
    delete_session_response = requests.request("DELETE", delete_session_url, headers=headers, data=payload)
    print("deleted session")
    return response.text


@app.route("/get_file_risk_guard",methods = ['GET'])
@track_emissions(output_dir="static",project_name="Panacea")
def get_file_risk_guard():
    dbParams = json.loads(request.args.get("dbParams"))
    filePath = dbParams['selectedFile']
    userName = dbParams['userName']
    wspName = dbParams['wspName']
    file_path = workspace_dir_path+'/'+filePath
    url = "https://us.api.opentext.com/mtm-riskguard/api/v1/process"
    payload = {}
    token = get_opentext_auth_token()
    headers = {
    'Authorization': 'Bearer '+token
    }
    with open(file_path, 'rb') as fobj:
        response = requests.request("POST", url, headers=headers, data=payload, files={"File":fobj})
    return response.json()

    
if __name__ == '__main__':
    #app.run(debug=True,port=80)
    # mlflow_process.terminate()
    app.run(host='0.0.0.0',port=80)
