"""Unicode, spelling and transliteration helpers shared by search and the assistant."""
import re
import unicodedata
from difflib import SequenceMatcher, get_close_matches

STOP = set('что как это где когда почему расскажи объясни пожалуйста лекции лекция курсе курс about what how why where when please explain lecture course the and for with der die das und ist ein eine que los las con por una del che gli dei della come sono'.split())
TRANSLIT = dict(zip('абвгдеёзийклмнопрстуфхц', ['a','b','v','g','d','e','e','z','i','y','k','l','m','n','o','p','r','s','t','u','f','h','ts']))
TRANSLIT.update({'ж':'zh','ч':'ch','ш':'sh','щ':'shch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya'})
KEYBOARD = str.maketrans("qwertyuiop[]asdfghjkl;'zxcvbnm,.", 'йцукенгшщзхъфывапролджэячсмитьбю')

def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.casefold().replace('ё','е')) if not unicodedata.combining(c))

def transliterate(text):
    return ''.join(TRANSLIT.get(c, c) for c in normalize(text))

def terms(text):
    words = re.findall(r'[^\W_]+', normalize(text), re.UNICODE)
    result = []
    for word in words:
        if re.search(r'[\u3400-\u9fff]', word):
            result.extend(word[i:i+2] for i in range(max(1,len(word)-1)))
        elif len(word) >= 2 and word not in STOP:
            result.append(word)
    return set(result)

def variants(query, vocabulary):
    result = [query]
    # Wrong keyboard layout is evaluated as an alternative, never replaces the original.
    if re.search('[a-z]', query.lower()):
        result.append(query.lower().translate(KEYBOARD))
    folded = {transliterate(w): w for w in sorted(vocabulary)}
    corrected = []
    for word in re.findall(r'[^\W_]+', normalize(query)):
        if word in STOP or word in vocabulary or len(word) < 4:
            corrected.append(word)
            continue
        key = transliterate(word)
        matches = get_close_matches(key, folded, n=1, cutoff=.78 if len(key)>=5 else .82)
        corrected.append(folded[matches[0]] if matches else word)
    result.append(' '.join(corrected))
    return list(dict.fromkeys(x for x in result if x.strip()))[:3]

def lexical_score(query_terms, document_terms):
    if not query_terms or not document_terms:
        return 0.0
    folded = {transliterate(t) for t in document_terms}
    scores=[]
    for term in query_terms:
        key=transliterate(term)
        if term in document_terms or key in folded:
            scores.append(1.0)
        else:
            candidates = (x for x in folded if len(key)>=4 and abs(len(x)-len(key))<=2)
            best=max((SequenceMatcher(None,key,x).ratio() for x in candidates),default=0)
            scores.append(best*.9 if best >= (.78 if len(key)>=5 else .82) else 0)
    return sum(scores)/len(scores)
