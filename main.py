import os
from flask import Flask, request, render_template, jsonify
from parser import parser
import pandas as pd
import re
import pandas as pd

app = Flask(__name__)

def parse_output(text):
    #Function to parse CG output and return dataframe of lemma, wordform, mut tag, pos tag etc
    #

    entries = []
    current_word = None
    capture_next = False
    lines = text.strip().splitlines()

    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # If this is a wrapper line: e.g. "<ddaer>"
        if line.startswith('"') and line.endswith('"') and '[' not in line and ':' not in line:
            current_word = line.strip('"<>')
            capture_next = True
            continue

        # This is an analysis line
        if capture_next:
            try:
                # Extract wordform in quotes
                first_quote_end = line.find('"', 1)
                wordform = line[1:first_quote_end]

                # Extract lang in []
                lang_start = line.find('[', first_quote_end)
                lang_end = line.find(']', lang_start)
                lang = line[lang_start + 1:lang_end]

                # Extract lemma (between colons)
                lemma_start = line.find(':', lang_end)
                lemma_end = line.find(':', lemma_start + 1)
                lemma = line[lemma_start + 1:lemma_end]

                # Tokens between [lang] and :lemma:
                between = line[lang_end + 1:lemma_start].strip()
                tokens = between.split()
                simple_tag = tokens[0] if tokens else None
                pos_tag = "".join(tokens) if tokens else None

                # After lemma
                after_lemma = line[lemma_end + 1:].strip()
                parts = after_lemma.split()
                
                mut_tag = parts[0] 

                # Sentence ID: in curly braces
                sent_id = parts[1]
                if sent_id.startswith('{') and sent_id.endswith('}'):
                    sent_id = sent_id[1:-1]

                if len(parts) > 2:
                    mut_reason = parts[2] 
                else:
                    mut_reason = None

                ## BANDAID HOTFIX YR as GYR
                if wordform == "yr" and lemma == "gyr":
                    print("Wordform yr!")
                    simple_tag = "YFB"
                    pos_tag = "YFB"
                    lemma = "y"
                    mut_tag = "+0m"
                    mut_reason = None
                ## HOTFIX wedi as gwadu
                if wordform == "wedi" and lemma == "gwadu":
                    simple_tag = "U"
                    pos_tag = "UBerf"
                    lemma = "wedi"
                    mut_tag = "+0m"
                    mut_reason = None
                ## fel as mêl
                if wordform == "fel" and lemma == "mêl":
                    simple_tag = "Cys"
                    pos_tag = "Cyscyd"
                    lemma = "fel"
                    mut_tag = "+0m"
                    mut_reason = None
                ## dim as tîm
                if wordform == "dim" and lemma == "tîm":
                    simple_tag = "Adf"
                    pos_tag = "Adf"
                    lemma = "dim"
                    mut_tag = "+0m"
                    mut_reason = None
                ## dy as tŷ
                if wordform == "dy" and lemma == "tŷ":
                    simple_tag = "Rha"
                    pos_tag = "Rhadib2u"
                    lemma = "dy"
                    mut_tag = "+0m"
                    mut_reason = None
                ## di (dy..di) shouldnt be labelled sm
                if wordform == "di" and pos_tag == "Rhadib2u":
                    mut_tag = "+0m"
                    mut_reason = None

                entries.append({
                    "wordform": wordform,
                    "lang": lang,
                    "simple_tag": simple_tag,
                    "pos_tag": pos_tag,
                    "lemma": lemma,
                    "mut_tag": mut_tag,
                    "sent_id": sent_id,
                    "mut_reason": mut_reason,
                })

            except Exception as e:
                print(f"Skipping malformed line: {line}<br><br>Reason: {e}")
            finally:
                capture_next = False
    return pd.DataFrame(entries)


def reason_explain(reason_tag, mut_tag, wordform, lemma, pos_tag):
    #Code to generate explanations. Template exists for all family, some require extra details.
    mut_map = {
        "+sm" : "soft mutation",
        "+nm" : "nasal mutation",
        "+am" : "aspirate mutation",
        "+hm" : "h-prothesis"
    }
    gender_map = {
        "B" : "feminine",
        "G" : "masculine"
    }
    pos_map = {
        "Be" : "verb-noun",
        "Ebu" : "feminine singular noun",
        "Ebll" : "feminine plural noun",
        "Egu" : "masculine singular noun",
        "Egll" : "masculine plural noun",
        "Anscadu" : "adjective",
        "Bdyf3u" : "verb",

    }
    exp = ''
    if not reason_tag or '-' not in reason_tag:
        return "Sorry, this mutation doesn't have a recognized explanation format."
    parts = reason_tag.split('-')

    if len(parts) > 2:
        trigger = parts[1:]
    else:
        trigger = parts[1]
    
    if 'POSS' in reason_tag:
        exp = "Possessive pronouns or determiners cause different types of mutation. "
        clitics = ['TH', 'M', 'W', 'U', 'N']
        if trigger == any(clitics):
            trigger = "'" + trigger
            trigger = trigger.lower()
        if 'ei' in trigger:
            
            gender = trigger[1]
            exp += f"The word <b>'{trigger}'</b> of gender {gender_map.get(gender,gender)} causes {mut_map.get(mut_tag,mut_tag)} on the word after. In this case, <b>{trigger}</b> makes <b>{lemma}</b> become <b>{wordform}</b>. <br><br>Note that ei is both the feminine and masculine possessive pronoun. The masculine causes soft mutation, the feminine causes aspirate mutation."
            return exp
        
        exp += f"The word <b>'{trigger}'</b> causes {mut_map.get(mut_tag,mut_tag)} on the following word. In this case, <b>{trigger}</b> makes <b>{lemma}</b> become <b>{wordform}</b>."
    if 'PREP' in reason_tag:
        if '_self' in reason_tag:
            exp = "The prepositions TROS, TAN and TRWY are often seen in their soft-mutated forms DROS, DAN, DRWY."
            return exp
        exp = "Some prepositions in Welsh cause mutation. "
        
        exp += f"The word <b>'{trigger}'</b> causes {mut_map.get(mut_tag,mut_tag)} on the following word. In this case, <b>{trigger}</b> makes <b>{lemma}</b> become <b>{wordform}</b>."
    if 'ADF' in reason_tag:
        
        if trigger == "ddim":
            exp = f"The word <b>dim</b> used to negate sentences is mutated to <b>ddim</b> when used adverbially. "
        exp = "Adverbs of time or measure cause mutation. Words which indicate 'when', 'how often', or 'for how long' something takes place undergo soft mutation."
        
        if trigger == "dydd":
            exp += f"The word <b>dydd</b> mutates into <b>ddydd</b> when talking about actions occurring on a specific day."
            return exp
        exp += f"The word <b>{trigger}</b> causes {mut_map.get(mut_tag,mut_tag)} on the following word. In this case, <b>{trigger}</b> makes <b>{lemma}</b> become <b>{wordform}</b>."
    if 'SIMP' in reason_tag:
        
        
        if reason_tag == "+SIMP-a":
            exp = f"The word <b>'{trigger}'</b> as a pronoun or predicative particle causes {mut_map.get(mut_tag,mut_tag)} on the word after. In this case, <b>{trigger}</b> makes <b>{lemma}</b> become <b>{wordform}</b>. <br><br>Not to be confused with 'a' as a conjunction, which causes aspirate mutation."
            return exp
        if reason_tag == "+SIMP-A":
            exp = f"The word <b>'{trigger}'</b> as a conjunction causes {mut_map.get(mut_tag,mut_tag)} on the word after. In this case, <b>{trigger}</b> makes <b>{lemma}</b> become <b>{wordform}</b>. <br><br>Not to be confused with 'a' as a pronoun or predicative particle, which cause soft mutation."
            return exp
        
        exp = f"The word <b>'{trigger}'</b> always causes {mut_map.get(mut_tag,mut_tag)} on the word after. In this case, <b>{trigger}</b> makes <b>{lemma}</b> become <b>{wordform}</b>. "
    if 'PREADJ' in reason_tag:
        
        if 'any' in reason_tag:
            exp = f"The previous word is an adjective placed before the noun, causing {mut_map.get(mut_tag,mut_tag)} on the word after. In this case, <b>{lemma}</b> becomes <b>{wordform}</b>. <br><br>In Welsh, adjectives are expected to go after the noun. In poetry and prose, as a literary device, an adjective may go before the noun and cause soft mutation."
            return exp
        
        exp = f"The word <b>{trigger}</b> is an adjective which goes before the noun, and always causes {mut_map.get(mut_tag,mut_tag)}. In this case, <b>{trigger}</b> makes <b>{lemma}</b> become <b>{wordform}</b>. <br><br>In Welsh, adjectives are expected to go after the noun. A few adjectives go before, and cause soft mutation."
    if 'NUM' in reason_tag:
        if 'un' in reason_tag:
            exp = f"The word <b>{trigger}</b> is a numeral which causes {mut_map.get(mut_tag,mut_tag)} on the word after if it is feminine. Certain numerals cause soft mutation, sometimes depending on the gender. In this case, <b>{trigger}</b> makes <b>{lemma}</b> become <b>{wordform}</b> because it is a feminine word. "
        exp = f"The word <b>{trigger}</b> is a numeral which always causes {mut_map.get(mut_tag,mut_tag)} on the word after. Certain numerals cause soft mutation, sometimes depending on the gender. In this case, <b>{trigger}</b> makes <b>{lemma}</b> become <b>{wordform}</b>. "
    if 'FEM' in reason_tag:
        if trigger == "y":
            exp = f"The word <b>{lemma}</b> is a {pos_map.get(pos_tag,pos_tag)} which mutates softly after the definite article Y/'r. Because of this, <b>{lemma}</b> mutates into <b>{wordform}</b> under {mut_map.get(mut_tag,mut_tag)}."
        if trigger == "adj":
            exp = f"The word <b>{lemma}</b> is an adjective which mutates softly when describing a singular feminine noun. Because of this, <b>{lemma}</b> mutates into <b>{wordform}</b> under {mut_map.get(mut_tag,mut_tag)}. <br><br>Exceptions to this rule are: 'braf', 'gyferbyn' never mutate. In North Wales, 'bach' often withstands the mutation. By convention, 'nos da' and 'wythnos diwethaf' are long standing exceptions too."
        if trigger == "nounadj":
            exp = f"The word <b>{lemma}</b> is a noun acting as an adjective which mutates softly when describing a singular feminine noun. Because of this, <b>{lemma}</b> mutates into <b>{wordform}</b> under {mut_map.get(mut_tag,mut_tag)}.  <br><br>Exceptions to this rule: when the function of the noun is genitive (indicating possession), e.g. Prifysgol Cymru, Llywodraeth Lloegr. Two long established exceptions are 'Eglwys Loegr' and 'Gŵyl Ddewi'."
        if trigger == "numfem":
            exp = f"The word <b>{lemma}</b> is a numeral which mutates softly when preceded by the definite article and followed by a singular feminine noun. Because of this, <b>{lemma}</b> mutates into <b>{wordform}</b> under {mut_map.get(mut_tag,mut_tag)}."
        if trigger == "yadj":
            exp = f"The word <b>{lemma}</b> is an adjective which mutates softly when falling between the definite article 'y' and a singular feminine noun. Because of this, <b>{lemma}</b> mutates into <b>{wordform}</b> under {mut_map.get(mut_tag,mut_tag)}."
    if 'RULE' in reason_tag:
        
        if trigger == "inflectedobj":
            exp = f"The word <b>{lemma}</b> is a {pos_map.get(pos_tag,pos_tag)} which mutates softly as the object of an inflected verb. Because of this, <b>{lemma}</b> mutates into <b>{wordform}</b> under {mut_map.get(mut_tag,mut_tag)}."
        if trigger == "ydau" or trigger == "ydwy":
            exp = f"The word <b>{lemma}</b> is a numeral which mutates softly regardless of gender when preceded by the definite article. Because of this, <b>{lemma}</b> mutates into <b>{wordform}</b> under {mut_map.get(mut_tag,mut_tag)}"
        if trigger == "rhaid":
            exp = f"The word <b>{lemma}</b> is a {pos_map.get(pos_tag,pos_tag)} which mutates softly as the object of the Rhaid pattern, which notably skips over the subject. Because of this, <b>{lemma}</b> mutates into <b>{wordform}</b> under {mut_map.get(mut_tag,mut_tag)}."
        if trigger == "yn":
            exp = f"The word <b>{lemma}</b> is a {pos_map.get(pos_tag,pos_tag)} which mutates softly after 'yn'. Because of this, <b>{lemma}</b> mutates into <b>{wordform}</b> under {mut_map.get(mut_tag,mut_tag)}. <br><br>In this case, 'yn' is the predicative particle (not the locative preposition). Adjectives and nouns mutate softly after the predicative 'yn'. Exceptions are those that begin with 'll' or 'rh'."
        if trigger == "adjv":
            exp = f"The word <b>{lemma}</b> is a verb-noun which mutates softly when described by an adjective. Because of this, <b>{lemma}</b> mutates into <b>{wordform}</b> under {mut_map.get(mut_tag,mut_tag)}."
        if trigger == "fodpred":
            exp = f"The word <b>{lemma}</b> is the verb to be in Welsh, and it can be used to link clauses together. When it is the subject of a noun-predicate sentence, in English it would be translated as 'that', and it mutates softly. Because of this, <b>{lemma}</b> mutates into <b>{wordform}</b> under {mut_map.get(mut_tag, mut_tag)}.  "
        if trigger == "ni":
            exp = f"The word <b>{lemma}</b> is a verb in a negative sentence. In Standard Welsh, these sentences should start with the particle 'Ni', which causes mixed mutation, but are often omitted, though the mutation remains. Because of this, <b>{lemma}</b> mutates into <b>{wordform}</b> under {mut_map.get(mut_tag, mut_tag)}."
        if trigger == "a":
            exp = f"The word <b>{lemma}</b> is a verb in a question. In Standard Welsh, these sentences should start with the particle 'a', which causes soft mutation, but are often omitted, though the mutation remains. Because of this, <b>{lemma}</b> mutates into <b>{wordform}</b> under {mut_map.get(mut_tag, mut_tag)}."
        if trigger == "angen":
            exp = f"The word <b>{lemma}</b> is a {pos_map.get(pos_tag,pos_tag)} which mutates softly as the object of the Angen pattern, which notably skips over the subject. Because of this, <b>{lemma}</b> mutates into <b>{wordform}</b> under {mut_map.get(mut_tag,mut_tag)}."

    if 'INTP' in reason_tag:
        exp = f"The word <b>{trigger}</b> causes <b>{lemma}</b> to mutate to <b>{wordform}</b> because of interpolation. When words are in an unexpected order, this causes soft mutation."
    return exp

def mut_setup(text):
    #Function to take the text, parse on Cytag, get mut_exp tags and return as dataframe.
    p = parser()
    
    output = p.get_output(text)
    #print("RAW OUTPUT:<br><br>", output)
    df = parse_output(output)
    
    mut_map = {
        "+sm" : "soft mutation",
        "+nm" : "nasal mutation",
        "+am" : "aspirate mutation",
        "+hm" : "h-prothesis"
    }
    
    

    #print(df)
    explanations = []

    for _, word in df.iterrows():
        if word['mut_tag'] != "+0m" and word['mut_reason']:
            exp = reason_explain(word['mut_reason'], word['mut_tag'], word['wordform'], word['lemma'], word['pos_tag'])
        elif word['mut_tag'] != "+0m":
            exp = "Sorry, this mutation doesn't have a reason yet. WIP!"
        else:
            exp = ""
            
        explanations.append(exp)
    df['explanation'] = explanations

    return df


def tests():
    #function to apply testing on the eval data, record results and return to csv.
    
    print("Testing phase start.")
    eval_data = pd.read_csv('eval.csv')
    copy_df = eval_data.copy()

    total = len(eval_data)
    correct = 0

    for i, row in enumerate(eval_data.itertuples(index=True), start=1):
        print(f"row: {i}")
        target = row.target
        gold = row.gold_reason
        res = mut_setup(row.sentence)

        # Try direct match
        if (res['wordform'] == target).any():
            matching_row = res[res['wordform'] == target]
        # Try fallback for hyphenated targets
        elif '-' in target:
            new_target = target.split('-')[0] + '-'
            if (res['wordform'] == new_target).any():
                matching_row = res[res['wordform'] == new_target]
            else:
                print("- in target but still no wordform found!")
                copy_df.loc[row.Index, 'pred'] = "Word not found"
                continue
        else:
            print(f"No word in {' '.join(res['wordform'])} matches the target {target}")
            copy_df.loc[row.Index, 'pred'] = "Word not found"
            continue

        mut_detected = matching_row['mut_tag'].iloc[0]
        print(mut_detected)
        if mut_detected != '+0m':
            mut_reason = matching_row['mut_reason'].iloc[0]
            if mut_reason:
                pred = mut_reason.split('+')[1]
                copy_df.loc[row.Index, 'pred'] = pred
                if pred == gold:
                    correct += 1
                    print("Correct!")
                else:
                    print(f"Reason mismatch, {pred} != gold: {gold}")
            else:
                copy_df.loc[row.Index, 'pred'] = "No mut reason detected."
                print("No mut reason detected.")
        else:
            print("No mut detected at all.")
            copy_df.loc[row.Index, 'pred'] = "No mut detected."

    print(f"{correct}/{total} = {correct/total:.2f} = {correct/total*100:.1f}%")
    print(copy_df)
    copy_df.to_csv('res.csv')
    return None

#tests()
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        welsh_text = request.form.get('welsh_txt', '')
        df = mut_setup(welsh_text)

        #extract data
        mutated_words = []
        for _, row in df.iterrows():
            
            mut_reason_class = row['mut_reason'].split('-')[0].split('+')[1].lower() if row['mut_reason'] else ''
            
            mutated_words.append({
                    'wordform': row['wordform'],
                    'pos_tag': row['pos_tag'],
                    'mut_tag': row['mut_tag'],
                    'mut_reason': row['mut_reason'],
                    'mut_reason_class': mut_reason_class,
                    'explanation': row['explanation']
            })
        return render_template('index.html',
                               welsh_text=welsh_text,
                               mutated_words=mutated_words)
    else:

        return render_template('index.html', welsh_text='', mutated_words=[])


if __name__ == '__main__':
   app.run(debug=True)