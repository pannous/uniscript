"""Random uniscript lines built from tricky fragments, one per line, deterministic (seed 1); fed to differential.sh"""
import random

SEED = 1
LINES = 3000
FRAGMENTS = [
    "<:alpha>", "\\:infinity", "\\:", "\\:nosuch", "<:nosuchthing>", "<:", "<:>", "<:/greek>", "<:greek>", "<:fracture>",
    "<:egyptian>", "<:/egyptian>", "<:<>", "<::>", "<<::>", "<:less>:", "<:fracture A b c >", "<:greek athos>", "<:greek c>",
    "<:mirror red A>", "<:red mirror 狗>", "<:red 𓀀>", "<:beside 犭 句>", "<:above 𓀀 𓁐>", "<:beside a b>",
    "<:egyptian seated man>", "<:egyptian man-sitting>", "<:bold italic alpha>", "<:greek bold a>", "<:double bold A>",
    "<:bold fraktur A>", "<:sans bold italic Omega>", "<:mirror bold italic A>", "<:font cuneiform-hittite>",
    "<:/font>", "<:font Santakku>", "<:color #ff8800 A b>", "<:color red;x A>", "<:color #ff8800 angle 90 alpha>",
    "<:lang ja>", "<:/lang>", "<:size 2em>", "<:/size>", "<:color blue mirror e>", "<:angle>", "<:angle 90 B>",
    "<:uniscript>", '<:uniscript version="https://uniscript.org/v9">', "<:double-d>", "<:upper a>", "<:iconic ⚠>",
    "<:red circle>", "<:mirror red circle>", "<:reverse red R>", "<:color #ff8800 é>", "<:bold ϑ>", "<:italic ω>",
    "a", "b", " ", "  ", "x", "7", "é", "🏴\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F", "α", "𝔄", "日本語",
    "A\U000E0072\U000E004D", "\U000E003A\U000E0063\U000E006F\U000E006C\U000E006F\U000E0072\U000E0020\U000E0072\U000E0065\U000E0064\U000E007F",
    "\U000E003C\U000E002F\U000E0066\U000E006F\U000E006E\U000E0074\U000E007F", "<", ">", ":", "\\", "-", "\t", "　", " ",
]

random.seed(SEED)
for _ in range(LINES):
    print("".join(random.choice(FRAGMENTS) for _ in range(random.randint(1, 8))))
