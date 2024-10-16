import logging
import asyncio
import threading
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
import numpy as np  
import requests
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC, SVR
from .models import UserChat 
from rest_framework.views import APIView
from asgiref.sync import sync_to_async
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error

# Configuración del logger
logging.basicConfig(level=logging.INFO)

# Datos para el entrenamiento
# Leer datos del archivo JSON
with open('data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Preparar los datos para el entrenamiento
X_con_valor = []
y_valor_con_valor = []

X_sin_valor = []
y_intencion_sin_valor = []

for d in data:
    if 'valor' in d:
        X_con_valor.append(d['mensaje'])
        y_valor_con_valor.append(d['valor'])
    else:
        X_sin_valor.append(d['mensaje'])
        y_intencion_sin_valor.append(d['intencion'])

# Entrenamiento del modelo de intención
X_train_intencion, X_test_intencion, y_train_intencion, y_test_intencion = train_test_split(
    X_sin_valor, y_intencion_sin_valor, test_size=0.2, random_state=42
)

model_intencion = make_pipeline(TfidfVectorizer(), SVC(kernel='linear'))
model_intencion.fit(X_train_intencion, y_train_intencion)

# Entrenamiento del modelo de valor
X_train_valor, X_test_valor, y_train_valor, y_test_valor = train_test_split(
    X_con_valor, y_valor_con_valor, test_size=0.2, random_state=42
)

model_valor = make_pipeline(TfidfVectorizer(), RandomForestRegressor())
model_valor.fit(X_train_valor, y_train_valor)

# Evaluar los modelos
accuracy_intencion = model_intencion.score(X_test_intencion, y_test_intencion)
logging.info(f"Precisión del modelo de intención: {accuracy_intencion:.2f}")

mse_valor = mean_squared_error(y_test_valor, model_valor.predict(X_test_valor))
logging.info(f"MSE del modelo de valor: {mse_valor:.2f}")

TOKEN = '7403419655:AAHMOvKS4I89l0Y0nwkS5MKFmFAdHj7jF6Q'  # Reemplaza con tu token real

# Almacena el estado del chat
user_responses = {}
application = ApplicationBuilder().token(TOKEN).build()
bot_running = False

nltk.download('punkt')
nltk.download('punkt_tab')
nltk.download('stopwords')
stop_words = set(stopwords.words('spanish'))

# def storeChatId(user_id, chat_id):
#     UserChat.objects.update_or_create(
#         user_id=user_id,
#         defaults={'chat_id': chat_id}
#     )

def callProducts():
    # Obtiene los productos de la base de datos
    url = f'http://localhost:8000/firebase/getdata/'
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Error: {response.status_code}")
        return None

def CallGetData(category, valor):
    logging.info(f"category en callgetdata: {category},  valor: {valor}")

    url = f'http://localhost:8000/firebase/getdata/?category={category}&valor={valor}'
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Error: {response.status_code}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    logging.info(f"Usuario iniciado: {user_id}")
    user_responses[user_id] = '¡Hola! ¿Qué estás buscando?'
    await context.bot.send_message(chat_id=user_id, text=user_responses[user_id])

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    productos = callProducts()
    logging.info(f"categorias traidas: {productos}")
    
    user_id = update.effective_chat.id
    user_input = update.message.text
    logging.info(f"Mensaje recibido de {user_id}: {user_input}")

    if user_input == '/start':
        await start(update, context)
    else:
        prediccion_intencion = model_intencion.predict([user_input])
        intencion = prediccion_intencion[0]
        logging.info(f"intencion desde handle_message: {intencion}")
        
        # valor = None
        
        numeros_str = ''
        
        if intencion in productos:
            if any(char.isdigit() for char in user_input):
                numeros = [char for char in user_input if char.isdigit()]
                
                # Unir los caracteres numéricos en una cadena
                numeros_str = ''.join(numeros)
                print(numeros_str)
                # prediccion_valor = model_valor.predict([user_input])
                print(user_input)
                # print(prediccion_valor)
                # valor = prediccion_valor[0]  
        if numeros_str: 
            logging.info(f"Intención: {intencion}, Valor: {numeros_str}")
        else:
            logging.info(f"Intención: {intencion}")
        
        if intencion == 'saludos':
            user_responses[user_id] = 'Por favor, escribe que te gustaría buscar.'
            await context.bot.send_message(chat_id=user_id, text=user_responses[user_id])
        elif intencion in productos:
            recommendedProducts = CallGetData(intencion, numeros_str)
            
            primeraVez = True
            if recommendedProducts:
                for product in recommendedProducts:
                    
                    if primeraVez:
                        if numeros_str:
                            primeraVez = False
                            user_responses[user_id] = 'Claro, te recomendaré los productos disponibles que estén en ese precio.'
                            await context.bot.send_message(chat_id=user_id, text=user_responses[user_id])
                        else:
                            primeraVez = False
                            user_responses[user_id] = 'Te recomendaré los productos disponibles.'
                            await context.bot.send_message(chat_id=user_id, text=user_responses[user_id])
                    else:
                        # Crear el botón
                        keyboard = [
                            [InlineKeyboardButton("Ver producto", url=f"https://tnm8rkjk-4200.use2.devtunnels.ms/product/{product['id']}")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)

                        # Enviar la imagen con el nombre del producto y el botón
                        await context.bot.send_photo(
                            chat_id=user_id,
                            photo=product['image'],
                            caption=f"<b>{product['productName']}</b>\nPrecio: {product['price']}$",
                            parse_mode='HTML',
                            reply_markup=reply_markup
                        )
            else: 
                user_responses[user_id] = 'Lo siento, no hay productos disponibles.'
                await context.bot.send_message(chat_id=user_id, text=user_responses[user_id])
        else:
            mensaje = "Lo siento, ese producto no está disponible"
            user_responses[user_id] = mensaje
            await context.bot.send_message(chat_id=user_id, text=user_responses[user_id])

def run_bot():
    global application
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)

    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
    new_loop.run_until_complete(application.run_polling())

@api_view(['GET'])
def StartChat(request):
    global bot_running
    if not bot_running:
        logging.info("Solicitud recibida para iniciar el chat.")
        bot_running = True
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.start()
        return Response({'mensaje': "Chat iniciado."}, status=status.HTTP_200_OK)
    else:
        return Response({'mensaje': "El chat ya está en ejecución."}, status=status.HTTP_400_BAD_REQUEST)

# @api_view(['POST'])
# def iniciar_chat(request):
#     mensaje = request.data.get('mensaje')

#     if not mensaje:
#         return Response({'error': 'Se debe enviar un mensaje en el cuerpo de la solicitud.'}, status=400)

#     url = f'https://api.telegram.org/bot{TOKEN}/getUpdates'
#     try:
#         response = requests.get(url)
#         data = response.json()

#         logging.info(f"Respuesta de getUpdates: {data}")

#         if data['ok']:
#             if data['result']:
#                 latest_update = data['result'][-1]
#                 chat_id = latest_update['message']['chat']['id']
#                 update = Update.de_json(latest_update, application.bot)
#                 context = ContextTypes.DEFAULT_TYPE(application.bot, update)

#                 # Aquí debes usar await
#                 handle_message(update, context)

#                 logging.info(f"Mensaje enviado a chat_id {chat_id}: {mensaje}")
#                 return Response({'chat_id': chat_id, 'mensaje': "Chat iniciado."}, status=200)
#             else:
#                 return Response({'error': 'No hay mensajes recientes.'}, status=404)
#         else:
#             return Response({'error': 'Error al obtener actualizaciones.'}, status=500)

#     except Exception as e:
#         return Response({'error': str(e)}, status=500)

# Iniciar el bot cuando se carga el servidor
if __name__ == "__main__":
    run_bot()