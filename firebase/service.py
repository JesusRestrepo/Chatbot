import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def get_recommendations(df, category=None, productName=None, min_price=None, max_price=None, num_recommendations=10):
    
  #Si tiene nombre de producto buscar por nombre de producto
  if productName:
    filtered_df = df[df['productName'].str.contains(productName, case=False)]
  else:
      filtered_df = df[df['category'].str.contains(category, case=False)]

  # Filtrar por rango de precios
  if min_price:
    filtered_df = filtered_df[filtered_df['price'] >= min_price]
  if max_price:
    filtered_df = filtered_df[filtered_df['price'] <= max_price]

  # Seleccionar un número aleatorio de productos del filtro
  return filtered_df.sample(n=num_recommendations)