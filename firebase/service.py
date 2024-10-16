import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def get_recommendations(df, category=None, valor=None, num_recommendations=10):
  
  if valor != '':
    print(valor)
    df['price'] = df['price'].str.replace('.', '', regex=False).astype(float) 
    filtered_df = df[df['category'].str.contains(category, case=False) & (df['price'] == float(valor))]
    print(filtered_df)
    if filtered_df.empty:
        return []
  else:
    filtered_df = df[df['category'].str.contains(category, case=False)]
    if filtered_df.empty:
        return []


  # Seleccionar un número aleatorio de productos del filtro
  if len(filtered_df) < num_recommendations:
    return filtered_df.sample(n=len(filtered_df))
  else:
    return  filtered_df.sample(n=num_recommendations)
