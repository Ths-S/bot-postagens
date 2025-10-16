import os
import json
import pickle
import base64
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

def get_youtube_service():
    """Carrega o token do secret e inicializa o serviço do YouTube"""
    token_b64 = os.getenv("TOCKEN_PICKLE_COMPLETE")

    if not token_b64:
        raise Exception("❌ Nenhum token encontrado. Configure TOCKEN_PICKLE_COMPLETE nos Secrets do GitHub.")

    # Decodifica o token
    token_bytes = base64.b64decode(token_b64)
    with open("token_temp.pickle", "wb") as f:
        f.write(token_bytes)

    with open("token_temp.pickle", "rb") as token_file:
        creds = pickle.load(token_file)

    # Se o token estiver expirado, tenta renovar
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    # Inicializa o serviço da API YouTube
    return build("youtube", "v3", credentials=creds)

def get_youtube_metrics():
    """Obtém estatísticas do canal"""
    youtube = get_youtube_service()

    request = youtube.channels().list(
        part="statistics",
        mine=True
    )
    response = request.execute()
    return response["items"][0]["statistics"]
