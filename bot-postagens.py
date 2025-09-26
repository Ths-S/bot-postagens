import schedule
import time
import json
from datetime import datetime

# ==============================
# FUNÇÕES DE POSTAGEM (placeholders)
# ==============================

def postar_youtube(video, titulo, descricao):
    print(f"[YouTube] Postando: {video} | Título: {titulo}")
    # TODO: integrar com YouTube Data API v3


def postar_instagram(video, legenda):
    print(f"[Instagram] Postando: {video} | Legenda: {legenda}")
    # TODO: integrar com Instagram Graph API


def postar_facebook(video, legenda):
    print(f"[Facebook] Postando: {video} | Legenda: {legenda}")
    # TODO: integrar com Facebook Graph API


def postar_tiktok(video, legenda):
    print(f"[TikTok] Postando: {video} | Legenda: {legenda}")
    # TODO: usar API de terceiros (ex: PrimeAPI) ou Selenium


# ==============================
# GERENCIADOR DE POSTAGENS
# ==============================

def executar_postagem(tarefa):
    rede = tarefa["rede"]
    video = tarefa["video"]
    titulo = tarefa.get("titulo", "")
    descricao = tarefa.get("descricao", "")
    legenda = tarefa.get("legenda", "")

    if rede == "youtube":
        postar_youtube(video, titulo, descricao)
    elif rede == "instagram":
        postar_instagram(video, legenda)
    elif rede == "facebook":
        postar_facebook(video, legenda)
    elif rede == "tiktok":
        postar_tiktok(video, legenda)
    else:
        print(f"[ERRO] Rede não suportada: {rede}")


# ==============================
# CARREGAR TAREFAS DO ARQUIVO
# ==============================

def carregar_tarefas():
    with open("tarefas.json", "r", encoding="utf-8") as f:
        return json.load(f)


def agendar_tarefas(tarefas):
    for tarefa in tarefas:
        hora_postagem = tarefa["hora"]  # Exemplo: "2025-09-26 18:00"
        dt = datetime.strptime(hora_postagem, "%Y-%m-%d %H:%M")
        hora_formatada = dt.strftime("%H:%M")

        # Agenda a tarefa
        schedule.every().day.at(hora_formatada).do(executar_postagem, tarefa)

        print(f"[AGENDADO] {tarefa['rede']} | {tarefa['video']} às {hora_formatada}")


# ==============================
# LOOP PRINCIPAL
# ==============================

if __name__ == "__main__":
    tarefas = carregar_tarefas()
    agendar_tarefas(tarefas)

    print("[BOT RODANDO] Aguardando horários de postagem...")
    while True:
        schedule.run_pending()
        time.sleep(30)
