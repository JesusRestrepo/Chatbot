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
from sklearn.svm import SVC
from .models import UserChat 
from rest_framework.views import APIView
from asgiref.sync import sync_to_async

# Configuración del logger
logging.basicConfig(level=logging.INFO)

# Datos para el entrenamiento
# Leer datos del archivo JSON
with open('data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Preparar los datos para el entrenamiento
X = [d['mensaje'] for d in data]
y = [d['intencion'] for d in data]

# Dividir los datos en conjuntos de entrenamiento y prueba
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Crear un pipeline para vectorización y clasificación con SVM
model = make_pipeline(TfidfVectorizer(), SVC(kernel='linear'))

# Entrenar el modelo
model.fit(X_train, y_train)

# Evaluar el modelo
accuracy = model.score(X_test, y_test)
logging.info(f"Precisión del modelo: {accuracy:.2f}")

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

def CallGetData(category):
    logging.info(f"category en callgetdata: {category}")
    url = f'http://localhost:8000/firebase/getdata/?category={category}'
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
    productos = ['pantalones', 'camisas', 'camisetas', 'zapatos', 'vestidos', 'chaquetas', 'otros']
    user_id = update.effective_chat.id
    user_input = update.message.text
    logging.info(f"Mensaje recibido de {user_id}: {user_input}")

    # storeChatId(update.message.from_user.id, user_id)

    if user_input == '/start':
        await start(update, context)
    else:
        prediccion = model.predict([user_input])
        intencion = prediccion[0]
        logging.info(f"intencion desde handle_message: {intencion}")
        if intencion == 'saludos':
            user_responses[user_id] = 'Por favor, escribe que te gustaría buscar.'
            await context.bot.send_message(chat_id=user_id, text=user_responses[user_id])
        elif intencion in productos:
            recommendedProducts = CallGetData(intencion)
            # mensaje = f"Claro, te recomiendo 5 productos que te van a gustar: {recommendedProducts}."
            # logging.info(f"se recomendó: {recommendedProducts}")
            # user_responses[user_id] = mensaje
            # await context.bot.send_message(chat_id=user_id, text=mensaje)
            primeravez = True
            for product in recommendedProducts:
                if  primeravez:
                    mensaje = f"Claro, te recomiendo 5 productos que te van a gustar"
                    user_responses[user_id] = mensaje
                    await context.bot.send_message(chat_id=user_id, text=mensaje)
                    primeravez = False
                else:
                    mensaje = f"Te recomiendo: {product['productName']}\n{product['image']}"
                    logging.info(f"se recomendó: {mensaje}")
                    user_responses[user_id] = mensaje
                    await context.bot.send_message(chat_id=user_id, text=mensaje)
        else:
            mensaje = "Lo siento, ese producto no está disponible"
            user_responses[user_id] = mensaje
            await context.bot.send_message(chat_id=user_id, text=mensaje)         

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