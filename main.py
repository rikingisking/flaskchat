import subprocess
import sys

def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# 必要なライブラリをインストール
for package in ['Flask', 'mysql-connector-python', 'openai', 'pinecone-client', 'requests']:
    try:
        __import__(package)
    except ImportError:
        install_package(package)

import openai
import mysql.connector
from flask import Flask, request, render_template
import json
import os
from pinecone import Pinecone, ServerlessSpec

# OpenAI APIキーの設定
openai.api_key = "key"

# Pineconeインスタンスの作成
pc = Pinecone(api_key="b7c39aa9-8c20-403a-8fba-f9636e43bfd7")

# Pineconeインデックスの作成または接続
index_name = "ddoraemon"
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=1536,  # ベクトルの次元数
        metric='euclidean',
        spec=ServerlessSpec(
            cloud='aws',
            region='us-east-1'
        )
    )
index = pc.Index(index_name)

# インデックスにベクトルをアップロード
def upsert_vectors():
    prompt = "Describe Doraemon's personality traits"
    embedding = openai.Embedding.create(input=prompt, model="text-embedding-ada-002")["data"][0]["embedding"]
    index.upsert(
        vectors=[
            {
                "id": "ddoraemon_001", 
                "values": embedding, 
                "metadata": {"text": "Doraemon's personality traits", "description": "Traits such as kind, thoughtful, etc."}
            }
        ]
    )

# ベクトルのアップロードを実行
upsert_vectors()

# MySQLの接続情報
DB_CONFIG = {
    'user': 'your_mysql_user',
    'password': 'your_mysql_password',
    'host': 'your_mysql_host',
    'database': 'doraemon_responses'
}

# Flaskアプリケーションの設定
app = Flask(__name__)

def analyze_emotion(prompt):
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=f"Please analyze the emotion in the following text and provide an emotional score between 0 and 1:\n\n{prompt}",
        max_tokens=10,
    )
    score = float(response.choices[0].text.strip())
    return score

def get_personality_traits():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT trait FROM personality")
        results = cursor.fetchall()
        conn.close()
        return " ".join([row['trait'] for row in results])
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return ""

def get_secret_gadgets():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT name, usage, episode FROM secret_gadgets")
        results = cursor.fetchall()
        conn.close()
        return results
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return []

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/query", methods=["POST"])
def query():
    prompt = request.form["prompt_text"]
    emotion_score = analyze_emotion(prompt)
    
    personality_traits = get_personality_traits()
    gadgets_info = get_secret_gadgets()

    # 質問の埋め込み生成
    query_embedding = openai.Embedding.create(input=prompt, model="text-embedding-ada-002")["data"][0]["embedding"]

    # Pineconeで関連文書の検索
    result = index.query(
        vector=query_embedding,
        top_k=10,
        include_values=True,
        include_metadata=True
    )

    related_texts = [match["metadata"]["text"] for match in result["matches"]]

    # 応答スタイルの決定
    if emotion_score > 0.5:
        response_style = "empathic"
    else:
        response_style = "logical"

    # 生成モデルに関連文書をプロンプトとして提供
    full_prompt = f"ユーザーの質問: {prompt}\n\n関連情報:\n{related_texts}\n\nドラえもんとして回答してください。応答スタイルは{response_style}です。:"
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are Doraemon."},
            {"role": "user", "content": full_prompt}
        ]
    )
    answer = response["choices"][0]["message"]["content"]

    return render_template("answer.html", answer=answer)

if __name__ == "__main__":
    app.run(debug=True)
