import os
import random
from fastapi import FastAPI, Request
from supabase import create_client, Client
import google.generativeai as genai

app = FastAPI()

SUPABASE_URL = "https://denjotdadkeqgbhaumgn.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRlbmpvdGRhZGtlcWdiaGF1bWduIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk2MjM0MzcsImV4cCI6MjA5NTE5OTQzN30.X0bDSYKDMIgYvNYWtKpRweFbyXboS8Az-FVU_nJNa7Q
")
GEMINI_KEY = os.environ.get("GEMINI_KEY", "AIzaSyAPJX0SKjH_UrSMxPGunZrOHSUa5Hb7TdQ")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_KEY)

# 🔮 78장 유니버셜 타로 카드 전체 리스트 (수파베이스의 card_name과 철자가 같아야 합니다)
ALL_CARDS = [
    "The Fool", "The Magician", "The High Priestess", "The Empress", "The Emperor",
    "The Hierophant", "The Lovers", "The Chariot", "Strength", "The Hermit",
    "Wheel of Fortune", "Justice", "The Hanged Man", "Death", "Temperance",
    "The Devil", "The Tower", "The Star", "The Moon", "The Sun", "Judgement", "The World",
    "Ace of Wands", "Two of Wands", "Three of Wands", "Four of Wands", "Five of Wands",
    "Six of Wands", "Seven of Wands", "Eight of Wands", "Nine of Wands", "Ten of Wands",
    "Page of Wands", "Knight of Wands", "Queen of Wands", "King of Wands",
    "Ace_of_Cups", "Two_of_Cups", "Three_of_Cups", "Four_of_Cups", "Five_of_Cups",
    "Six_of_Cups", "Seven_of_Cups", "Eight_of_Cups", "Nine_of_Cups", "Ten_of_Cups",
    "Page_of_Cups", "Knight_of_Cups", "Queen_of_Cups", "King_of_Cups",
    "Ace of Swords", "Two of Swords", "Three of Swords", "Four of Swords", "Five of Swords",
    "Six of Swords", "Seven of Swords", "Eight of Swords", "Nine of Swords", "Ten of Swords",
    "Page of Swords", "Knight of Swords", "Queen of Swords", "King of Swords",
    "Ace of Pentacles", "Two of Pentacles", "Three of Pentacles", "Four of Pentacles", "Five of Pentacles",
    "Six of Pentacles", "Seven of Pentacles", "Eight of Pentacles", "Nine of Pentacles", "Ten of Pentacles",
    "Page of Pentacles", "Knight of Pentacles", "Queen of Pentacles", "King of Pentacles"
]

def get_card_interpretation(card_name: str) -> str:
    try:
        response = supabase.table("tarot_db").select("interpretation").eq("card_name", card_name).execute()
        if response.data:
            return response.data[0]["interpretation"]
        return f"({card_name} 임상 지식 없음)"
    except:
        return "(조회 실패)"

@app.post("/tarot")
async def kakao_tarot_handler(request: Request):
    try:
        kakao_body = await request.json()
        params = kakao_body.get("action", {}).get("params", {})
        
        user_question = params.get("question", "올해의 전체적인 운세")
        
        num1 = params.get("card1")
        num2 = params.get("card2")
        num3 = params.get("card3")
        
        chosen_cards = []
        
        # [갈래길 1] 손님이 랜덤 셔플 버튼을 누르고 곧바로 날아온 경우
        if num1 is None or num2 is None or num3 is None:
            chosen_cards = random.sample(ALL_CARDS, 3) # 비복원 추출로 중복 원천 차단
            prefix_msg = "🔮 마스터가 온 힘을 다해 셔플한 3장의 카드 결과입니다!\n\n"
            
        # [갈래길 2] 손님이 직접 숫자를 치고 온 경우
        else:
            prefix_msg = "🎴 의뢰인이 직접 우주의 기운을 담아 고른 번호의 결과입니다!\n\n"
            nums = [int(num1), int(num2), int(num3)]
            
            # 🔥 중복 방지 순환 로직
            for n in nums:
                card_index = (n - 1) % len(ALL_CARDS) # 1~78 범위를 안전하게 맞춤
                candidate_card = ALL_CARDS[card_index]
                
                # 만약 이미 앞에서 뽑힌 카드 이름이라면? 중복 감지!
                if candidate_card in chosen_cards:
                    # 아직 안 뽑힌 남은 카드들 중에서 무작위로 한 장 대체 처분
                    remaining_cards = [c for c in ALL_CARDS if c not in chosen_cards]
                    candidate_card = random.choice(remaining_cards)
                
                chosen_cards.append(candidate_card)
        
        card1, card2, card3 = chosen_cards[0], chosen_cards[1], chosen_cards[2]
        
        # 수파베이스 매칭
        know1 = get_card_interpretation(card1)
        know2 = get_card_interpretation(card2)
        know3 = get_card_interpretation(card3)
        
        # 제미나이 입체 연산
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction="너는 20년 경력의 명품 타로 마스터야. 주어지는 3카드 임상지식을 바탕으로 질문에 대한 소름 돋는 종합 해석을 신비로운 톤으로 해줘."
        )
        
        user_prompt = f"질문: {user_question}\n\n1. 과거: {card1} ({know1})\n2. 현재: {card2} ({know2})\n3. 미래: {card3} ({know3})"
        completion = model.generate_content(user_prompt)
        
        final_reading = prefix_msg + completion.text
        
    except Exception as e:
        final_reading = f"🔮 마스터의 기운이 고르지 못합니다. 다시 시도해 주세요! (오류: {str(e)})"

    return {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": final_reading}}]
        }
    }
