from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

def compute_similarity(user_question, bot_response):
    question_emb = model.encode(user_question, convert_to_tensor=True)
    cosine_scores = list()

    high_score_res = list() # 放分數較高的回答

    # 計算每個回答與問題相似度
    for bs in bot_response:
        response_emb = model.encode(bs, convert_to_tensor=True)
        score = util.cos_sim(question_emb, response_emb)
        print(f"the score: {score.item()}")
        cosine_scores.append(score)

    for i in range(0, len(bot_response)):
        if cosine_scores[i] > 0.5:  # 篩選分數高於 threshold 的回答
            high_score_res.append(bot_response[i])

    return high_score_res