# Phase 7 — Portuguese review NLP (lexicon baseline; BERTimbau is the upgrade path)

Reviews (unique review_id): 98410; with message: 40641; with title: 11517

## Sentiment vs score
Mean lexicon sentiment by review score: {1: -0.063, 2: -0.042, 3: 0.009, 4: 0.074, 5: 0.122}
Spearman rho(sentiment, score) = 0.5504 (p=0); inconsistencies = 235
Sample 5-star-negative-text reviews:
  - score=1 sentiment=0.20: Nem fizeram a nota fiscal 
  - score=4 sentiment=-0.33: Correios não entregou 
  - score=2 sentiment=0.17: Excelente produto indico a qualquer pessoa.
  - score=5 sentiment=-0.18: Recomendo para todos, não tive problema nenhum, mercadoria e prazo ótimos.
  - score=4 sentiment=-0.20: Ainda não utilizei o produto

## Near-duplicate review detection
- minhash candidate pairs checked: 819,375,921; near-dup pairs (>0.4 band match): 0 (rate 0.000000)
- duplicate review_id across orders: 0 (the known quirk; graph keeps one row)
