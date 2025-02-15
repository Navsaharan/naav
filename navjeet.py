import websocket_client as websocket
import json
import requests
import pandas as pd
import time
import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt
import smtplib
import psycopg2
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, send_file
from flask_socketio import SocketIO
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from email.mime.text import MIMEText
from twilio.rest import Client
import telegram
import talib  # Library for technical indicators
from textblob import TextBlob  # For sentiment analysis
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
import logging
import random
from collections import deque

# Alpha Vantage API Key
ALPHA_VANTAGE_API_KEY = "PLN7K0APZNMJS2V3"
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"

# Initialize logging
logging.basicConfig(filename='trade_log.txt', level=logging.INFO, format='%(asctime)s - %(message)s')

# Database Connection
DB_CONN = psycopg2.connect(
    dbname="trading_db",
    user="your_db_user",
    password="your_db_password",
    host="your_db_host",
    port="5432"
)
DB_CURSOR = DB_CONN.cursor()
DB_CURSOR.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        phone VARCHAR(15),
        telegram_chat_id VARCHAR(50),
        role VARCHAR(10) DEFAULT 'trader'
    );
''')
DB_CURSOR.execute('''
    CREATE TABLE IF NOT EXISTS trade_history (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        stock_symbol VARCHAR(10),
        trade_type VARCHAR(10),
        price FLOAT,
        quantity INT,
        stop_loss FLOAT,
        take_profit FLOAT,
        risk_factor FLOAT,
        status VARCHAR(20),
        mode VARCHAR(10) DEFAULT 'PAPER'
    );
''')
DB_CONN.commit()

# Flask Setup
app = Flask(__name__)
app.secret_key = 'supersecretkey'
socketio = SocketIO(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Fetch real-time stock data from Alpha Vantage
def fetch_stock_data(symbol):
    params = {
        "function": "TIME_SERIES_INTRADAY",
        "symbol": symbol,
        "interval": "5min",
        "apikey": ALPHA_VANTAGE_API_KEY
    }
    response = requests.get(ALPHA_VANTAGE_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        time_series = data.get("Time Series (5min)", {})
        if time_series:
            latest_timestamp = sorted(time_series.keys())[-1]
            latest_data = time_series[latest_timestamp]
            return {
                "symbol": symbol,
                "price": float(latest_data["1. open"])
            }
    return {"error": "Failed to fetch stock data"}

@app.route('/stock-price/<symbol>')
def get_stock_price(symbol):
    stock_data = fetch_stock_data(symbol)
    return jsonify(stock_data)

# Simulated paper trading execution
def execute_paper_trade(user_id, stock_symbol, trade_type, quantity):
    stock_data = fetch_stock_data(stock_symbol)
    if "error" in stock_data:
        return stock_data
    
    trade_price = stock_data["price"]
    DB_CURSOR.execute("INSERT INTO trade_history (stock_symbol, trade_type, price, quantity, status) VALUES (%s, %s, %s, %s, 'Executed')",
                     (stock_symbol, trade_type, trade_price, quantity))
    DB_CONN.commit()
    return {"message": "Paper trade executed", "price": trade_price, "quantity": quantity}

@app.route('/paper-trade', methods=['POST'])
@login_required
def paper_trade():
    data = request.json
    stock_symbol = data['stock_symbol']
    trade_type = data['trade_type']
    quantity = data['quantity']
    result = execute_paper_trade(current_user.id, stock_symbol, trade_type, quantity)
    return jsonify(result)

if __name__ == "__main__":
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
