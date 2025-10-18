def get_instagram_metrics(metadata):
    print("📸 Coletando métricas do Instagram...")

    base_url = "https://graph.instagram.com"
    fields = (
        "id,caption,media_type,media_url,thumbnail_url,timestamp,"
        "permalink,like_count,comments_count,children{media_url,media_type}"
    )
    url = f"{base_url}/{IG_USER_ID}/media?fields={fields}&access_token={GRAPH_API_TOKEN}"

    all_posts = []
    try:
        # 🔁 Paginação — busca todas as páginas
        while url:
            r = requests.get(url)
            data = r.json()

            if "error" in data:
                print("❌ Erro retornado pela API:", data["error"])
                break

            posts = data.get("data", [])
            all_posts.extend(posts)

            # Verifica se há próxima página
            url = data.get("paging", {}).get("next")

    except Exception as e:
        print("❌ Erro ao acessar a API do Instagram:", e)
        return {"summary": {}, "posts": []}

    if not all_posts:
        print("⚠️ Nenhum post encontrado. Verifique GRAPH_API_TOKEN e IG_USER_ID.")
        return {"summary": {}, "posts": []}

    insta_metrics = []
    total_likes = total_comments = 0

    for post in all_posts:
        caption = post.get("caption", "")
        like_count = post.get("like_count", 0)
        comments_count = post.get("comments_count", 0)
        total_likes += like_count
        total_comments += comments_count

        # tenta associar o post com metadados existentes
        match = next(
            (v for k, v in metadata.items() if caption and caption.strip() in v.get("description", "")),
            None
        )

        insta_metrics.append({
            "id": post.get("id"),
            "caption": caption,
            "media_type": post.get("media_type"),
            "media_url": post.get("media_url"),
            "thumbnail_url": post.get("thumbnail_url"),
            "permalink": post.get("permalink"),
            "timestamp": post.get("timestamp"),
            "likes": like_count,
            "comments": comments_count,
            "children": post.get("children", {}).get("data", []),
            "matched_metadata": match
        })

    summary = {
        "totalPosts": len(insta_metrics),
        "totalLikes": total_likes,
        "totalComments": total_comments,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }

    print(f"✅ Coletados {len(insta_metrics)} posts do Instagram.")

    return {"summary": summary, "posts": insta_metrics}
