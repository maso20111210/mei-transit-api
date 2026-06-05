from flask import Flask, jsonify, request
import swisseph as swe
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)

# 本命盤資料（小梅）
NATAL = {
    'sun':     {'sign': 'pisces',      'deg': 25.45},
    'moon':    {'sign': 'scorpio',     'deg': 19.47},
    'asc':     {'sign': 'leo',         'deg': 23.80},
    'mercury': {'sign': 'pisces',      'deg': 22.80},
    'venus':   {'sign': 'aquarius',    'deg': 9.83},
    'mars':    {'sign': 'aquarius',    'deg': 3.45},
    'mc':      {'sign': 'taurus',      'deg': 22.05},
}

# 星座起始黃道度數
SIGN_START = {
    'aries': 0, 'taurus': 30, 'gemini': 60, 'cancer': 90,
    'leo': 120, 'virgo': 150, 'libra': 180, 'scorpio': 210,
    'sagittarius': 240, 'capricorn': 270, 'aquarius': 300, 'pisces': 330
}

# 本命星絕對黃道度數
NATAL_ABS = {
    name: SIGN_START[data['sign']] + data['deg']
    for name, data in NATAL.items()
}

# Swiss Ephemeris 行星對應
PLANET_IDS = {
    'sun':     swe.SUN,
    'moon':    swe.MOON,
    'mercury': swe.MERCURY,
    'venus':   swe.VENUS,
    'mars':    swe.MARS,
    'jupiter': swe.JUPITER,
    'saturn':  swe.SATURN,
}

PLANET_ZH = {
    'sun': '太陽', 'moon': '月亮', 'mercury': '水星',
    'venus': '金星', 'mars': '火星', 'jupiter': '木星', 'saturn': '土星'
}

NATAL_ZH = {
    'sun': '本命太陽', 'moon': '本命月亮', 'mercury': '本命水星',
    'venus': '本命金星', 'mars': '本命火星', 'asc': '上升', 'mc': '天頂'
}

ASPECT_ZH = {
    'conjunction': '合相', 'sextile': '六合',
    'square': '刑相', 'trine': '三分', 'opposition': '對分'
}

ASPECTS = [
    ('conjunction', 0, 8),
    ('sextile',    60, 6),
    ('square',     90, 7),
    ('trine',     120, 7),
    ('opposition',180, 8),
]

def get_aspect(angle_diff):
    diff = abs(angle_diff) % 360
    if diff > 180:
        diff = 360 - diff
    for name, deg, orb in ASPECTS:
        if abs(diff - deg) <= orb:
            return name
    return None

def calc_transits(dt_utc):
    jd = swe.julday(
        dt_utc.year, dt_utc.month, dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60.0
    )
    transits = []
    for planet_name, planet_id in PLANET_IDS.items():
        pos, _ = swe.calc_ut(jd, planet_id)
        transit_deg = pos[0]
        for natal_name, natal_deg in NATAL_ABS.items():
            diff = transit_deg - natal_deg
            aspect = get_aspect(diff)
            if aspect:
                transits.append({
                    'transit': planet_name,
                    'natal': natal_name,
                    'aspect': ASPECT_ZH[aspect],
                    'transit_zh': PLANET_ZH[planet_name],
                    'natal_zh': NATAL_ZH.get(natal_name, natal_name),
                    'transit_deg': round(transit_deg, 2),
                    'natal_deg': round(natal_deg, 2),
                })
    return transits

def score_transits(transits):
    score = 70
    GOOD = ['合相', '六合', '三分']
    BAD  = ['刑相', '對分']
    WEIGHT = {
        'jupiter': 3, 'venus': 2, 'sun': 2,
        'moon': 2, 'mars': -1, 'saturn': -2, 'mercury': 1
    }
    for t in transits:
        w = WEIGHT.get(t['transit'], 1)
        if t['aspect'] in GOOD:
            score += w * 3
        elif t['aspect'] in BAD:
            score += w * (-3)
    return max(40, min(99, score))

def score_to_level(score):
    if score >= 85: return '⭐⭐⭐⭐⭐ 超旺'
    if score >= 75: return '⭐⭐⭐⭐ 不錯'
    if score >= 60: return '⭐⭐⭐ 平穩'
    if score >= 50: return '⭐⭐ 留意'
    return '⭐ 謹慎'

LUCKY_NUMBERS = [3, 6, 7, 8, 9, 11, 18, 22]
LUCKY_COLORS  = ['珊瑚紅', '薰衣草紫', '天空藍', '金黃色', '翠綠色', '玫瑰金']
DIRECTIONS    = ['東南方', '正南方', '西南方', '正東方', '東北方']

@app.route('/transit')
def transit():
    mode = request.args.get('mode', 'today')
    tz = pytz.timezone('Asia/Taipei')
    now_local = datetime.now(tz)

    if mode == 'tomorrow':
        target_local = now_local + timedelta(days=1)
    else:
        target_local = now_local

    target_utc = target_local.astimezone(pytz.utc).replace(hour=12, minute=0, second=0)

    transits = calc_transits(target_utc)
    score    = score_transits(transits)
    level    = score_to_level(score)

    date_str = target_local.strftime('%Y/%m/%d')
    weekdays = ['一','二','三','四','五','六','日']
    weekday  = weekdays[target_local.weekday()]

    seed = target_local.day + target_local.month
    lucky_number = LUCKY_NUMBERS[seed % len(LUCKY_NUMBERS)]
    lucky_color  = LUCKY_COLORS[seed % len(LUCKY_COLORS)]
    direction    = DIRECTIONS[seed % len(DIRECTIONS)]

    return jsonify({
        'dateText':    f'{date_str}（週{weekday}）',
        'score':       score,
        'level':       level,
        'luckyNumber': lucky_number,
        'luckyColor':  lucky_color,
        'direction':   direction,
        'transits':    transits,
    })

@app.route('/')
def index():
    return jsonify({'status': 'ok', 'service': 'mei-transit-api'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
