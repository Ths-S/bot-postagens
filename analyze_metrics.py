import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

metrics_file = "data/metrics.json"
recommendations_file = "data/recommendations.json"
metadata_file = "metadata.json"

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def analyze(metrics):
    prompt = f"""
    Você é um especialista em marketing digital e funis de vendas.
    Analise os dados de performance abaixo e recomende ações práticas
    para aumentar o engajamento e os cliques nos links.

    Dados:
    {json.dumps(metrics, ensure_ascii=False, indent=2)}

    Responda com:
    - sugestões específicas para títulos, descrições e hashtags
    - horário ideal de postagem
    - formato de vídeo com melhor retenção
    - ideias de novos conteúdos baseadas em tendências
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )

    return response.choices[0].message.content.strip()

def update_metadata(recommendations):
    metadata = load_json(metadata_file)
    print("💡 Aplicando melhorias automáticas...")

    for k, v in metadata.items():
        v["title"] = v.get("title", "") + " 🔥"
        if "hashtags" not in v:
            v["tags"] = list(set(v.get("tags", []) + ["marketing", "otimização"]))
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print("✅ metadata.json atualizado com melhorias!")

def main():
    metrics = load_json(metrics_file)
    if not metrics:
        print("⚠️ Nenhum dado encontrado em metrics.json")
        return

    print("🧠 Analisando métricas com IA...")
    rec = analyze(metrics)
    with open(recommendations_file, "w", encoding="utf-8") as f:
        json.dump({"recommendations": rec}, f, indent=2, ensure_ascii=False)
    print("✅ Recomendações salvas em data/recommendations.json")

    update_metadata(rec)

if __name__ == "__main__":
    main()
