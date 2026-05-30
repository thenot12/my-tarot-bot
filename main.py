import os
import random
from fastapi import FastAPI, Request
from supabase import create_client, Client
import google.generativeai as genai

app = FastAPI()

# 🔑 수파베이스 및 제미나이 보안 키 설정
SUPABASE_URL = "https://denjotdadkeqgbhaumgn.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "YOUR_SUPABASE_ANON_KEY")
GEMINI_KEY = os.environ.get("GEMINI_KEY", "YOUR_GEMINI_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_KEY)

# 🔮 78장 유니버셜 타로 카드 전체 리스트 (Cups의 언더바를 공백으로 통일하여 수파베이스와 매칭 확률을 높였습니다)
ALL_CARDS = [
    "The Fool", "The Magician", "The High Priestess", "The Empress", "The Emperor",
    "The Hierophant", "The Lovers", "The Chariot", "Strength", "The Hermit",
    "Wheel of Fortune", "Justice", "The Hanged Man", "Death", "Temperance",
    "The Devil", "The Tower", "The Star", "The Moon", "The Sun", "Judgement", "The World",
    "Ace of Wands", "Two of Wands", "Three of Wands", "Four of Wands", "Five of Wands",
    "Six of Wands", "Seven of Wands", "Eight of Wands", "Nine of Wands", "Ten of Wands",
    "Page of Wands", "Knight of Wands", "Queen of Wands", "King of Wands",
    "Ace of Cups", "Two of Cups", "Three of Cups", "Four of Cups", "Five of Cups",
    "Six of Cups", "Seven of Cups", "Eight of Cups", "Nine of Cups", "Ten of Cups",
    "Page of Cups", "Knight of Cups", "Queen of Cups", "King of Cups",
    "Ace of Swords", "Two of Swords", "Three of Swords", "Four of Swords", "Five of Swords",
    "Six of Swords", "Seven of Swords", "Eight of Swords", "Nine of Swords", "Ten of Swords",
    "Page of Swords", "Knight of Swords", "Queen of Swords", "King of Swords",
    "Ace of Pentacles", "Two of Pentacles", "Three of Pentacles", "Four of Pentacles", "Five of Pentacles",
    "Six of Pentacles", "Seven of Pentacles", "Eight of Pentacles", "Nine of Pentacles", "Ten of Pentacles",
    "Page of Pentacles", "Knight of Pentacles", "Queen of Pentacles", "King of Pentacles"
]

def get_card_interpretation(card_name: str) -> str:
    try:
        # 안전하게 수파베이스에서 해석 데이터를 가져옵니다.
        response = supabase.table("tarot_db").select("interpretation").eq("card_name", card_name).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]["interpretation"]
        return f"({card_name} 임상 지식 없음)"
    except Exception as e:
        return f"(조회 실패: {str(e)})"

@app.post("/tarot")
async def kakao_tarot_handler(request: Request):
    try:
        kakao_body = await request.json()
        
        # 🚨 카카오톡이 빈 상자를 보냈을 때를 대비한 안전망 3중 장치
        action = kakao_body.get("action", {})
        if not action:
            action = {}
            
        params = action.get("params", {})
        if not params:
            params = {}
        
        # 1. 질문이 비어있으면 무조건 기본값으로 채워줍니다.
        user_question = params.get("question")
        if not user_question or str(user_question).strip() == "":
            user_question = "올해의 전체적인 운세와 흐름"
        
        num1 = params.get("card1")
        num2 = params.get("card2")
        num3 = params.get("card3")
        
        chosen_cards = []
        
        # 2. 손님이 직접 카드를 안 뽑았거나(랜덤 버튼), 카카오톡 설정이 누락되어 빈 값이 오면 자동으로 랜덤 셔플 작동!
        if num1 is None or num2 is None or num3 is None:
            chosen_cards = random.sample(ALL_CARDS, 3)
            prefix_msg = "🔮 마스터가 우주의 기운을 담아 셔플한 3장의 카드 결과입니다!\n\n"
            
        # 3. 손님이 직접 숫자를 고르고 온 경우 (안전하게 숫자로 변환 처리)
        else:
            prefix_msg = "🎴 의뢰인이 직접 고른 번호의 결과입니다!\n\n"
            try:
                nums = [int(num1), int(num2), int(num3)]
                
                for n in nums:
                    card_index = (n - 1) % len(ALL_CARDS)
                    candidate_card = ALL_CARDS[card_index]
                    
                    # 중복 카드 방지 로직
                    if candidate_card in chosen_cards:
                        remaining_cards = [c for c in ALL_CARDS if c not in chosen_cards]
                        candidate_card = random.choice(remaining_cards)
                    
                    chosen_cards.append(candidate_card)
            except:
                # 만약 숫자가 깨져서 들어오면 안전하게 랜덤으로 우회
                chosen_cards = random.sample(ALL_CARDS, 3)
        
        card1, card2, card3 = chosen_cards[0], chosen_cards[1], chosen_cards[2]
        
        # 데이터베이스 임상 지식 매칭
        know1 = get_card_interpretation(card1)
        know2 = get_card_interpretation(card2)
        know3 = get_card_interpretation(card3)
        
        # 제미나이 AI 해석 연산 (최신 모델 지정)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction="너는 20년 경력의 명품 타로 마스터야. 주어지는 3카드 임상지식을 바탕으로 질문에 대한 소름 돋는 종합 해석을 아주 신비롭고 친절한 톤으로 해줘."
        )
        
        user_prompt = f"질문: {user_question}\n\n1. 과거: {card1} ({know1})\n2. 현재: {card2} ({know2})\n3. 미래: {card3} ({know3})"
        completion = model.generate_content(user_prompt)
        
        final_reading = prefix_msg + completion.text
        
    except Exception as e:
        final_reading = f"🔮 마스터의 기운이 고르지 못합니다. 다시 시도해 주세요! (시스템 에러: {str(e)})"

    # 카카오톡 템플릿 규격에 맞춰 최종 반환
    return {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": final_reading}}]
        }
    }
