from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

texts=["minor cleanliness issue","small amount of trash","dusty classroom","minor cleaning required","broken classroom chair","projector not working","fan not working","printer problem","internet connection not working","wifi unavailable","network problem in lab","water leakage in bathroom","large water leakage","pipe leaking","electrical wire sparking","electric shock risk","major electrical problem","fire from electrical equipment","short circuit in laboratory","building wall damaged","ceiling damaged","major infrastructure damage","broken door","unsafe staircase"]
labels=["Low","Low","Low","Low","Medium","Medium","Medium","Medium","Medium","Medium","Medium","High","High","High","Critical","Critical","Critical","Critical","Critical","High","High","High","Medium","Critical"]
vectorizer=TfidfVectorizer()
model=LogisticRegression(max_iter=2000)
model.fit(vectorizer.fit_transform(texts),labels)

def predict_priority(text):
    if not text: return "Medium"
    return model.predict(vectorizer.transform([text]))[0]
