from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from firebase.service import get_recommendations

# Variable global para almacenar la instancia de Firebase
firebase_app = None
db = None

def initialize_firebase():
    global firebase_app, db
    if not firebase_app:
        cred_path = Path("C:/Users/jdrestrepo/Downloads/ecommerce-uswearfirebase-firebase-adminsdk-w08hg-311f8dac54.json")
        cred = credentials.Certificate(cred_path)
        firebase_app = firebase_admin.initialize_app(cred)
        db = firestore.client()

def GetProducts():
    initialize_firebase()
    users_ref = db.collection('products').stream()
    products_data = []
    for doc in users_ref:
        product = doc.to_dict()
        products_data.append(product)
    dfProducts = pd.DataFrame(products_data)
    return dfProducts

@api_view(['GET'])
def GetData(request):
    category = request.query_params.get('category') 
    valor = request.query_params.get('valor')
    print(f"category en GetData: {category}, valor : {valor}")

    dfProducts = GetProducts()
    if category and  valor:
        recommendedProducts = get_recommendations(dfProducts, category=category, valor=valor, num_recommendations=6)
        return Response(recommendedProducts.to_dict('records'), status=status.HTTP_200_OK)
    elif category:
        recommendedProducts = get_recommendations(dfProducts, category=category, num_recommendations=6)
        print(f'desde getdata la respuesta: {recommendedProducts}')
        return Response(recommendedProducts.to_dict('records'), status=status.HTTP_200_OK)
    else:
        unique_categories = dfProducts['category'].str.lower().unique().tolist()
        return Response(unique_categories, status=status.HTTP_200_OK)