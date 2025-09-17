QUESTIONS: list[dict[str, str]] = [
    {"key": "fav_color", "text": "Любимый цвет?"},
    {"key": "season", "text": "Любимое время года?"},
    {"key": "tea_or_coffee", "text": "Чай или кофе?"},
    {"key": "owl_or_lark", "text": "Сова или жаворонок?"},
    {"key": "cafe_order", "text": "Что скорее всего закажешь в кафе?"},
    {"key": "island_item", "text": "Что возьмёшь на необитаемый остров?"},
    {"key": "catchphrase", "text": "Какое слово чаще всего говоришь?"},
    {"key": "million_or_vacation", "text": "Миллион рублей или пожизненный отпуск?"},
    {"key": "childhood_assoc", "text": "Первая ассоциация с детством?"},
    {"key": "celebrity_like", "text": "Кого из знаменитостей ты больше всего напоминаешь?"},
    {"key": "funny_story", "text": "Самая смешная история с подружкой?"},
    {"key": "why_love", "text": "За что тебя можно любить бесконечно?"},
    {"key": "superpower", "text": "Если бы была суперспособность, то какая?"},
    {"key": "parallel_job", "text": "Кем бы работала в параллельной вселенной?"},
    {"key": "country_live", "text": "В какой стране хотела бы пожить?"},
    {"key": "what_lose_first", "text": "Что скорее всего потеряешь первым делом?"},
]


def get_question_text(index: int) -> str:
    return QUESTIONS[index]["text"]


def get_question_key(index: int) -> str:
    return QUESTIONS[index]["key"]
