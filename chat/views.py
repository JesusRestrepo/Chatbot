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
from telegram import Message, Chat
import httpx
from asgiref.sync import async_to_sync

# Configuración del logger
logging.basicConfig(level=logging.INFO)

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

# Evaluar los modelos
accuracy_intencion = model_intencion.score(X_test_intencion, y_test_intencion)
logging.info(f"Precisión del modelo de intención: {accuracy_intencion:.2f}")

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    logging.info(f"Usuario iniciado: {user_id}")
    user_responses[user_id] = '¡Hola! ¿Qué estás buscando?'
    await context.bot.send_message(chat_id=user_id, text=user_responses[user_id])

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"Update desde handle_message: {update}")
    user_id = update.effective_chat.id
    user_input = update.message.text
    logging.info(f"Mensaje recibido de {user_id}: {user_input}")

    response = {"text": "", "products": []}

    if user_input == '/start':
        await start(update, context)
        return response

    productos = await call_products()
    if productos is None:
        response["text"] = "No se pudo obtener productos."
        return response

    prediccion_intencion = model_intencion.predict([user_input])
    intencion = prediccion_intencion[0]
    logging.info(f"Intención desde handle_message: {intencion}")

    numeros_str = ''.join(filter(str.isdigit, user_input))

    if intencion in productos:
        recommended_products = await call_get_data(intencion, numeros_str)
        try:
            print(f'recommended_products desde handle_messages: {recommended_products}')
            if recommended_products:
                for product in recommended_products:
                    response["products"].append({
                        "image": product['image'],
                        "caption": f"{product['productName']}",
                        "price": f"{product['price']}$",
                        "url":f"https://tnm8rkjk-4200.use2.devtunnels.ms/product/{product['id']}"
                    })
                response["text"] = 'Claro, a continuación, te enviaré productos de acuerdo a lo que solicitaste.'
            else:
                response["text"] = 'Lo siento, no hay productos disponibles.'
        except Exception as e:
            logging.error(f"Error en handle_message: {e}")
            response["text"] = "Oops, ocurrió un error,  por favor inténtalo de nuevo."
            response['products'] = []
    elif intencion == 'saludos':
        response["text"] = "¡Hola! por favor, digita el producto de tu interés"
    else:
        response["text"] = "Lo siento, ese producto no está disponible."

    return response

async def call_products():
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get('http://localhost:8000/firebase/getdata/')
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logging.error(f"Error al llamar a los productos: {e}")
        return None
    except httpx.HTTPStatusError as e:
        logging.error(f"Error en la respuesta: {e}")
        return None

async def call_get_data(category, valor):
    logging.info(f"category en call_get_data: {category}, valor: {valor}")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if valor:
                url = f'http://localhost:8000/firebase/getdata/?category={category}&valor={valor}'
            else:
                url = f'http://localhost:8000/firebase/getdata/?category={category}'
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            # Limpieza de datos: eliminar o reemplazar NaN
            for product in data:
                product['price'] = product.get('price') if product.get('price') is not None else 0  # Reemplaza NaN con 0
                product['image'] = product.get('image') if product.get('image') else ""  # Reemplaza None con cadena vacía
                product['productName'] = product.get('productName') if product.get('productName') else "Sin nombre"  # Reemplaza None con "Sin nombre"

            return data
    except httpx.RequestError as e:
        logging.error(f"Error en la llamada a getdata: {e}")
        return None
    except httpx.HTTPStatusError as e:
        logging.error(f"Error en la respuesta: {e}")
        return None


def run_bot():
    global application
    new_loop = asyncio.new_event_loop()  # Crea un nuevo bucle de eventos
    asyncio.set_event_loop(new_loop)  # Establece el nuevo bucle como el actual

    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
    
    try:
        new_loop.run_until_complete(application.run_polling())  # Ejecuta el bot
    except Exception as e:
        logging.error(f"Error en el bucle del bot: {e}")
    finally:
        new_loop.close()  # Cierra el bucle de eventos al finalizar
    # global application
    # new_loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(new_loop)

    # application.add_handler(CommandHandler('start', start))
    # application.add_handler(MessageHandler(filters.TEXT, handle_message))
    # new_loop.run_until_complete(application.run_polling())

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

async def send_message_async(user_message, user_id):
    chat = Chat(id=user_id, type="private")
    message = Message(message_id=0, date=None, chat=chat, text=user_message)
    update = Update(update_id=0, message=message)
    context = ContextTypes.DEFAULT_TYPE(application.bot, update)

    print('antes de entrar al handle_message desde send_message_async')
    bot_response = await handle_message(update, context)
    print(f'desde  send_message_async: {bot_response}')


    response_data = {'text': bot_response["text"], 'products': bot_response["products"]}

    # Enviar productos si hay
    for product in bot_response["products"]:
        try:
            response = await application.bot.send_photo(
                chat_id=user_id,
                photo=product['image'],
                caption=product['caption'],
                parse_mode='HTML'
            )
            print(f"Respuesta de Telegram: {response}")
        except Exception as e:
            print(f"Error enviando la imagen: {e}")

    return response_data

@api_view(['POST'])
def send_message(request):
    user_message = request.data.get('message')
    user_id = request.data.get('user_id')

    if not user_message or not user_id:
        return Response({'error': 'Se debe enviar un mensaje y un user_id.'}, status=400)

    # Llamar a la función asíncrona usando async_to_sync
    response_data = async_to_sync(send_message_async)(user_message, user_id)
    print('---------------------------------------------------------------')
    print(f'response_data: {response_data}')
    
    return Response(response_data, status=200)

if __name__ == "__main__":
    run_bot()